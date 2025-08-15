"""
RutIA API - FastAPI Gateway Principal (TERMONUCLEAR COMPLETO)
Gateway para integración con n8n, Streamlit y sistemas externos
CON RUTA REAL DESDE AIRFLOW pgRouting + OSM
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import hashlib
import time
import uuid
import math

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import psycopg2
from psycopg2.extras import RealDictCursor
import h3
import requests
from dotenv import load_dotenv

# Importar motor espacial
import sys
sys.path.append('/app')
from core.spatial_engine import crear_motor_espacial, calcular_tiempo_estimado_h3

# Configuración
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# MODELOS PYDANTIC
# =============================================================================

class PedidoRequest(BaseModel):
    """Modelo para recibir pedidos desde n8n"""
    producto: str = Field(..., description="Producto solicitado")
    direccion: str = Field(..., description="Dirección de entrega")
    telefono: Optional[str] = Field(None, description="Teléfono cliente")
    cliente_nombre: Optional[str] = Field(None, description="Nombre cliente")
    mensaje_original: Optional[str] = Field(None, description="Mensaje original completo")
    
    @validator('direccion')
    def direccion_no_vacia(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError('Dirección debe tener al menos 5 caracteres')
        return v.strip()

class PedidoResponse(BaseModel):
    """Respuesta del procesamiento de pedido"""
    pedido_id: str
    status: str
    rider_asignado: Optional[str] = None
    tiempo_estimado_minutos: Optional[int] = None
    es_batch: bool = False
    mensaje_cliente: str
    airflow_dag_run_id: Optional[str] = None
    tienda_info: Optional[Dict[str, Any]] = None

class RiderInfo(BaseModel):
    """Información de rider"""
    id: int
    nombre: str
    lat: float
    lon: float
    h3_actual: str
    status: str
    pedidos_activos: int
    tiene_pedido_cerca_local: bool
    eficiencia_score: float

class TrackingInfo(BaseModel):
    """Información de tracking"""
    pedido_id: str
    status: str
    rider: Optional[RiderInfo] = None
    ubicacion_actual: Optional[Dict[str, float]] = None
    eta_minutos: Optional[int] = None
    ruta_calculada: Optional[Dict] = None
    es_batch: bool = False
    progreso_porcentaje: int = 0

class MetricasResponse(BaseModel):
    """Métricas del sistema en tiempo real"""
    riders_online: int
    pedidos_activos: int
    entregas_hoy: int
    tiempo_promedio_minutos: float
    eficiencia_batching: float
    h3_mas_demandado: Optional[str] = None
    timestamp: datetime

# MODELO FIXED PARA UBICACIÓN RIDER
class RiderUbicacionRequest(BaseModel):
    """Modelo para actualizar ubicación de rider"""
    lat: float
    lon: float
    pedido_id: Optional[str] = None
    progreso_pct: Optional[float] = None
    
class PedidoItem(BaseModel):
    """Item individual del pedido"""
    pedido_id: Optional[str] = None
    item_id: Optional[int] = None
    item_nombre: str
    item_precio: Optional[float] = None

class ClienteData(BaseModel):
    """Datos del cliente"""
    nombre: Optional[str] = None
    direccion: Optional[str] = None

class PedidoOriginal(BaseModel):
    """Estructura original del pedido"""
    items: Optional[List[dict]] = None
    total: Optional[float] = None
    cantidad_items: Optional[int] = None

class DataOriginal(BaseModel):
    """Data original completa"""
    cliente: Optional[ClienteData] = None
    pedido: Optional[PedidoOriginal] = None
    restaurant: Optional[str] = None
    timestamp: Optional[str] = None
    fecha_legible: Optional[str] = None

class PedidoRequestComplejo(BaseModel):
    """Modelo para recibir pedidos complejos desde n8n evolucionado"""
    # Campos principales
    message: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_direccion: Optional[str] = None
    
    # IDs y metadata
    pedido_id: Optional[str] = None
    restaurant: Optional[str] = None
    
    # Totales
    pedido_total: Optional[float] = None
    pedido_cantidad_items: Optional[int] = None
    
    # Timestamps
    pedido_timestamp: Optional[str] = None
    pedido_fecha_legible: Optional[str] = None
    
    # Items del pedido
    pedido_items: Optional[List[PedidoItem]] = None
    
    # Data original nested
    data_original: Optional[DataOriginal] = None
    
    # Campos legacy (por compatibilidad)
    producto: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    mensaje_original: Optional[str] = None
    
    def get_producto_principal(self) -> str:
        """Extraer producto principal del pedido complejo"""
        if self.producto:
            return self.producto
        
        if self.pedido_items and len(self.pedido_items) > 0:
            return self.pedido_items[0].item_nombre
        
        if self.message and "Hamburguesa" in self.message:
            return "Hamburguesa Gisera"
        
        return "Pedido Geográfico"
    
    def get_direccion(self) -> str:
        """Extraer dirección del pedido complejo"""
        if self.direccion:
            return self.direccion
        
        if self.cliente_direccion:
            return self.cliente_direccion
        
        if self.data_original and self.data_original.cliente:
            return self.data_original.cliente.direccion or "Dirección no especificada"
        
        return "Dirección no especificada"
    
    def get_cliente_nombre(self) -> str:
        """Extraer nombre del cliente"""
        nombre = None
        
        if self.cliente_nombre:
            nombre = self.cliente_nombre
        elif self.data_original and self.data_original.cliente:
            nombre = self.data_original.cliente.nombre or "Cliente"
        else:
            nombre = "Cliente"
        
        # DEBUG LOG
        logger.info(f"🔍 Debug cliente_nombre extraído: '{nombre}'")
        logger.info(f"🔍 self.cliente_nombre: {self.cliente_nombre}")
        
        return nombre
    
    def get_resumen_pedido(self) -> str:
        """Generar resumen del pedido"""
        if self.pedido_items:
            items_count = len(self.pedido_items)
            principal = self.pedido_items[0].item_nombre if items_count > 0 else "Items"
            
            if items_count == 1:
                return principal
            else:
                return f"{principal} + {items_count - 1} items más"
        
        return self.get_producto_principal()

# =============================================================================
# CONFIGURACIÓN FASTAPI
# =============================================================================

app = FastAPI(
    title="RutIA API",
    description="Ruteo Inteligente con IA - API Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: ["http://localhost:8501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# DEPENDENCIAS
# =============================================================================

def get_db_connection():
    """Dependency para conexión DB"""
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),  # ← CAMBIO: postgres en lugar de localhost
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'rutia_db'),
            user=os.getenv('POSTGRES_USER', 'rutia_admin'),
            password=os.getenv('POSTGRES_PASSWORD', 'espacial123')
        )
        return connection
    except Exception as e:
        logger.error(f"❌ Error conectando DB: {e}")
        raise HTTPException(status_code=500, detail="Error de base de datos")

def get_motor_espacial():
    """Dependency para motor espacial"""
    try:
        return crear_motor_espacial()
    except Exception as e:
        logger.error(f"❌ Error creando motor espacial: {e}")
        raise HTTPException(status_code=500, detail="Error motor espacial")
        
def limpiar_coordenadas_duplicadas(coordenadas: list, distancia_min_metros: float = 30.0) -> list:
    """🔧 Limpiar coordenadas duplicadas o muy cercanas"""
    if not coordenadas or len(coordenadas) < 2:
        return coordenadas
    
    coordenadas_limpias = [coordenadas[0]]  # Siempre incluir primera
    
    for coord in coordenadas[1:]:
        ultimo = coordenadas_limpias[-1]
        
        # Distancia aproximada en metros
        dlat = (coord[1] - ultimo[1]) * 111000
        dlon = (coord[0] - ultimo[0]) * 111000 * math.cos(math.radians(coord[1]))
        distancia_m = math.sqrt(dlat**2 + dlon**2)
        
        # Solo agregar si está suficientemente lejos
        if distancia_m >= distancia_min_metros:
            coordenadas_limpias.append(coord)
    
    logger.info(f"🔧 Coordenadas: {len(coordenadas)} → {len(coordenadas_limpias)} (removidas: {len(coordenadas) - len(coordenadas_limpias)})")
    return coordenadas_limpias

# =============================================================================
# ENDPOINTS PRINCIPALES
# =============================================================================

@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "service": "RutIA API",
        "description": "Ruteo Inteligente con IA para llegar mejor",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "pedidos": "/api/pedido",
            "riders": "/api/riders",
            "tracking": "/api/tracking/{pedido_id}",
            "metricas": "/api/metricas",
            "airflow": "/api/airflow/trigger"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check para monitoring"""
    try:
        # Test DB connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected", 
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/api/pedido", response_model=PedidoResponse)
async def procesar_pedido_complejo(
    pedido: PedidoRequestComplejo,  
    background_tasks: BackgroundTasks,
    db_conn = Depends(get_db_connection),
    motor_espacial = Depends(get_motor_espacial)
):
    """Procesar nuevo pedido complejo desde n8n evolucionado"""
    
    # Extraer datos usando métodos helper
    producto = pedido.get_producto_principal()
    direccion = pedido.get_direccion()
    cliente_nombre = pedido.get_cliente_nombre()
    resumen = pedido.get_resumen_pedido()
    
    logger.info(f"📱 Nuevo pedido: {resumen} → {direccion}")
    logger.info(f"👤 Cliente: {cliente_nombre}")  # DEBUG para ver qué extrae
    
    try:
        # Geocoding
        coords = motor_espacial.geocoding_inteligente(direccion)
        h3_destino = h3.geo_to_h3(coords[1], coords[0], 9)
        
        # Buscar rider
        # rider_result = motor_espacial.buscar_rider_optimo(h3_destino)
        rider_result = None
        
        # CONFIGURACIÓN TIENDA (desde .env)
        tienda_config = {
            "nombre": os.getenv('EMPRESA_NOMBRE', 'La Geográfica'),
            "direccion": os.getenv('EMPRESA_DIRECCION', 'Blanco Encalada 2680, CABA'),
            "lat": float(os.getenv('EMPRESA_LAT', -34.56077965377718)),
            "lon": float(os.getenv('EMPRESA_LON', -58.461592938922614))
        }
        
        pedido_id_final = pedido.pedido_id or f"RUT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        if rider_result:
            mensaje_cliente = f"🗺️ ¡Pedido recibido {cliente_nombre}!\n\n"
            mensaje_cliente += f"🔍 Geocodificando coordenadas espaciales de '{direccion}'...\n"
            mensaje_cliente += f"📐 Triangulando hexágonos H3 para optimización de ruta...\n"
            mensaje_cliente += f"🛵 Ejecutando algoritmos de asignación de riders...\n\n"
            mensaje_cliente += f"⚡ Tu {resumen} está siendo procesado con precisión cartográfica!\n"
            mensaje_cliente += f"📍 Origen: {tienda_config['nombre']}\n"
            mensaje_cliente += f"🎯 Destino: {direccion}\n"
            mensaje_cliente += f"🛵 Rider asignado: {rider_result.nombre}\n"
            mensaje_cliente += f"⏱️ Tiempo estimado: 25 min\n\n"
            mensaje_cliente += f"💫 La magia geoespacial está en marcha! 🚀"
            
            rider_asignado = rider_result.nombre
        else:
            mensaje_cliente = f"🗺️ ¡Pedido recibido {cliente_nombre}!\n\n"
            mensaje_cliente += f"🔍 Geocodificando coordenadas espaciales de '{direccion}'...\n"
            mensaje_cliente += f"📐 Triangulando hexágonos H3...\n"
            mensaje_cliente += f"🛵 Buscando rider disponible...\n\n"
            mensaje_cliente += f"📍 Origen: {tienda_config['nombre']}\n"
            mensaje_cliente += f"🎯 Destino: En análisis espacial...\n\n"
            mensaje_cliente += f"💫 Procesando con precisión cartográfica! 🚀"
            
            rider_asignado = None
        
        # RESPONSE CON TIENDA INFO
        response = PedidoResponse(
            pedido_id=pedido_id_final,
            status="procesando",  # Cambiar a "procesando" en lugar de "procesado"
            rider_asignado=rider_asignado,
            tiempo_estimado_minutos=25 if rider_result else None,
            es_batch=False,
            mensaje_cliente=mensaje_cliente,
            tienda_info=tienda_config  # AGREGAR ESTO
        )
        
        pedido_dict = pedido.dict()
        logger.info(f"🔍 DEBUG pedido_dict: {pedido_dict}")  # DEBUG
        background_tasks.add_task(trigger_airflow_dag_internal, pedido_data=pedido_dict)
        
        logger.info(f"✅ Pedido procesado: {pedido_id_final}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error procesando pedido: {e}")
        return PedidoResponse(
            pedido_id=f"ERR-{uuid.uuid4().hex[:8].upper()}",
            status="error",
            mensaje_cliente=f"❌ Error procesando pedido de {cliente_nombre}. Reintentando análisis espacial...",
            es_batch=False
        )
    finally:
        if 'motor_espacial' in locals():
            motor_espacial.close()
        if 'db_conn' in locals():
            db_conn.close()

async def trigger_airflow_dag_internal(pedido_data: dict):
    """Función INTERNA para trigger DAG de Airflow con los datos del pedido"""
    try:
        airflow_url = "http://airflow:8080/api/v1/dags/rutia_termonuclear_procesamiento_espacial/dagRuns"
        
        # Headers para autenticación Airflow (si es necesario)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic YXBpOmFwaTEyMw=='  # ← api:api123
        }
        
        payload = {
            "conf": pedido_data,
            "dag_run_id": f"rutia_{pedido_data.get('pedido_id', 'manual')}_{int(time.time())}"
        }
        
        logger.info(f"🌊 Triggering Airflow DAG con pedido: {pedido_data.get('pedido_id', 'N/A')}")
        
        response = requests.post(airflow_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Airflow DAG triggered exitosamente: {response.status_code}")
        else:
            logger.error(f"❌ Error Airflow HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout triggering Airflow DAG")
    except Exception as e:
        logger.error(f"❌ Error triggering Airflow: {e}")

@app.get("/api/riders", response_model=List[RiderInfo])
async def get_riders_disponibles(
    h3_area: Optional[str] = Query(None, description="Filtrar por área H3"),
    db_conn = Depends(get_db_connection)
):
    """Obtener riders disponibles con información espacial"""
    logger.info(f"🛵 Consultando riders disponibles (área: {h3_area})")
    
    try:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Query básica para demo
            query = """
            SELECT 
                id, nombre, 
                ST_Y(ubicacion_actual) as lat,
                ST_X(ubicacion_actual) as lon,
                h3_actual,
                pedidos_activos,
                tiene_pedido_cerca_local,
                eficiencia_score
            FROM riders 
            WHERE status = 'disponible'
            ORDER BY eficiencia_score DESC
            LIMIT 10;
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            riders = [
                RiderInfo(
                    id=r['id'],
                    nombre=r['nombre'],
                    lat=r['lat'] or -34.6037,
                    lon=r['lon'] or -58.3816,
                    h3_actual=r['h3_actual'] or '881f1a4a2ffffff',
                    status='disponible',
                    pedidos_activos=r['pedidos_activos'] or 0,
                    tiene_pedido_cerca_local=r['tiene_pedido_cerca_local'] or False,
                    eficiencia_score=r['eficiencia_score'] or 50.0
                )
                for r in results
            ]
            
            logger.info(f"✅ {len(riders)} riders encontrados")
            return riders
            
    except Exception as e:
        logger.error(f"❌ Error consultando riders: {e}")
        # Return empty list instead of raising
        return []
    finally:
        db_conn.close()

@app.get("/api/tracking/{pedido_id}")
async def get_tracking_pedido_completo(
    pedido_id: str,
    db_conn = Depends(get_db_connection)
):
    """🚀 TRACKING COMPLETO: Con coordenadas y sin errores"""
    logger.info(f"🗺️ Tracking COMPLETO para pedido: {pedido_id}")
    
    try:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            
            # 1. VERIFICAR PEDIDO CON LOGS
            logger.info(f"🔍 Step 1: Buscando pedido {pedido_id} en DB...")
            cursor.execute("""
                SELECT 
                    p.id, p.pedido_externo_id, p.cliente_nombre, p.cliente_direccion,
                    ST_Y(p.coordenadas_entrega) as cliente_lat,
                    ST_X(p.coordenadas_entrega) as cliente_lon,
                    p.h3_destino, p.tiempo_estimado_minutos, p.status, p.rider_id
                FROM pedidos p
                WHERE p.pedido_externo_id = %s
                LIMIT 1;
            """, (pedido_id,))
            
            pedido_data = cursor.fetchone()
            
            if not pedido_data:
                logger.error(f"❌ Step 1 FAIL: Pedido {pedido_id} NO ENCONTRADO en DB")
                raise HTTPException(status_code=404, detail=f"Pedido {pedido_id} no encontrado")
            
            logger.info(f"✅ Step 1 OK: Pedido encontrado - Cliente: {pedido_data['cliente_nombre']}")
            logger.info(f"📍 Coordenadas cliente: {pedido_data['cliente_lat']}, {pedido_data['cliente_lon']}")
            
            # 2. VERIFICAR COORDENADAS
            if pedido_data['cliente_lat'] == 0 and pedido_data['cliente_lon'] == 0:
                logger.error(f"❌ Step 2 CRITICAL: Cliente en [0,0] - GEOCODING FALLÓ en Airflow")
                logger.error(f"❌ Dirección: {pedido_data['cliente_direccion']}")
                
                # NO HARDCODEAR - Intentar geocoding de emergencia en la API
                try:
                    from core.spatial_engine import crear_motor_espacial
                    motor = crear_motor_espacial()
                    coords_emergency = motor.geocoding_inteligente(pedido_data['cliente_direccion'])
                    motor.close()
                    
                    pedido_data['cliente_lat'] = coords_emergency[1]
                    pedido_data['cliente_lon'] = coords_emergency[0] 
                    
                    logger.info(f"🔧 Step 2 EMERGENCY: Geocoding exitoso - {coords_emergency[1]}, {coords_emergency[0]}")
                    
                except Exception as geo_error:
                    logger.error(f"❌ Step 2 FAIL: Emergency geocoding falló: {geo_error}")
                    raise HTTPException(
                        status_code=422, 
                        detail=f"No se pudo geocodificar la dirección: {pedido_data['cliente_direccion']}"
                    )
            
            # 3. CONFIGURACIÓN TIENDA
            tienda_coords = {
                'lat': float(os.getenv('EMPRESA_LAT', -34.56077965377718)),
                'lon': float(os.getenv('EMPRESA_LON', -58.461592938922614)),
                'nombre': os.getenv('EMPRESA_NOMBRE', 'RutIA Demo'),
                'direccion': os.getenv('EMPRESA_DIRECCION', 'Blanco Encalada 2680, CABA')
            }
            
            logger.info(f"🏪 Step 3 OK: Tienda en {tienda_coords['lat']}, {tienda_coords['lon']}")
            
            # 4. VERIFICAR TABLA ROUTING
            logger.info(f"🔍 Step 4: Verificando tabla OSM routing...")
            try:
                cursor.execute("SELECT COUNT(*) as total FROM osm_calles_routing;")
                routing_count = cursor.fetchone()['total']
                logger.info(f"📊 Step 4 INFO: {routing_count} calles en tabla routing")
            except Exception as table_error:
                logger.warning(f"⚠️ Step 4 WARN: Tabla routing no existe - usando fallback")
                routing_count = 0
            
            if routing_count < 10:
                logger.warning(f"⚠️ Step 4 WARN: Pocas calles ({routing_count}) - usando fallback")
                ruta_real = None
            else:
                # 5. INTENTAR QUERY ROUTING CON COORDENADAS
                logger.info(f"🔍 Step 5: Ejecutando query pgRouting CON COORDENADAS...")
                
                rider_lon, rider_lat = tienda_coords['lon'], tienda_coords['lat']
                cliente_lon, cliente_lat = pedido_data['cliente_lon'], pedido_data['cliente_lat']
                
                try:
                    cursor.execute("""
                        WITH ruta_calculada AS (
                          SELECT r.seq, r.path_seq, r.node, r.edge, r.cost, r.agg_cost,
                                 e.geometria, e.nombre, e.tipo_highway, e.longitud_km
                          FROM pgr_dijkstra(
                              'SELECT id, source, target, cost, reverse_cost FROM osm_calles_routing',
                              (SELECT id FROM osm_calles_routing_vertices_pgr 
                               ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) LIMIT 1),
                              (SELECT id FROM osm_calles_routing_vertices_pgr 
                               ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) LIMIT 1),
                              false
                          ) AS r
                          LEFT JOIN osm_calles_routing e ON (r.edge = e.id)
                          WHERE r.edge IS NOT NULL
                          ORDER BY r.path_seq
                        )
                        SELECT 
                          COUNT(*) AS total_calles,
                          ROUND(SUM(longitud_km)::numeric, 2) AS distancia_total_km,
                          ROUND(SUM(cost)::numeric, 1) AS tiempo_total_minutos,
                          ARRAY_AGG(nombre ORDER BY path_seq) FILTER (WHERE nombre IS NOT NULL) AS calles_utilizadas,
                          ARRAY_AGG(tipo_highway ORDER BY path_seq) FILTER (WHERE tipo_highway IS NOT NULL) AS tipos_vias,
                          
                          ST_AsGeoJSON(
                            ST_LineMerge(
                              ST_Collect(geometria ORDER BY path_seq)
                            )
                          ) AS ruta_geojson_completa,
                          
                          json_agg(
                            ST_AsGeoJSON(geometria)::json -> 'coordinates'
                            ORDER BY path_seq
                          ) AS coordenadas_segmentos
                          
                        FROM ruta_calculada;
                    """, (rider_lon, rider_lat, cliente_lon, cliente_lat))
                    
                    ruta_real = cursor.fetchone()
                    logger.info(f"✅ Step 5 OK: Query ejecutada - {ruta_real['total_calles']} calles encontradas")
                    
                except Exception as routing_error:
                    logger.error(f"❌ Step 5 FAIL: Error en pgRouting: {routing_error}")
                    ruta_real = None
            
            # 6. PROCESAR RESULTADO CON COORDENADAS
            logger.info(f"🔍 Step 6: Procesando resultado...")
            
            if ruta_real and ruta_real['total_calles'] > 0:
                logger.info(f"✅ Step 6a: Usando ruta REAL con {ruta_real['total_calles']} calles")
                
                # 🔥 PROCESAR COORDENADAS
                coordenadas_completas = []
                
                # Agregar tienda al inicio
                coordenadas_completas.append([tienda_coords['lon'], tienda_coords['lat']])
                
                # Agregar coordenadas de la ruta
                if ruta_real.get('coordenadas_segmentos'):
                    for segmento_coords in ruta_real['coordenadas_segmentos']:
                        if segmento_coords and isinstance(segmento_coords, list):
                            coordenadas_completas.extend(segmento_coords)
                
                # Agregar cliente al final
                coordenadas_completas.append([pedido_data['cliente_lon'], pedido_data['cliente_lat']])
                
                # 🔧 FIX: LIMPIAR COORDENADAS DUPLICADAS
                coordenadas_completas = limpiar_coordenadas_duplicadas(coordenadas_completas, 30.0)
                
                ruta_termonuclear = {
                    'tipo': 'pgRouting_Dijkstra_REAL',
                    'algoritmo': 'Dijkstra',
                    'calles_extraidas_osm': int(ruta_real['total_calles']),
                    'distancia_total_km': float(ruta_real['distancia_total_km'] or 0.5),
                    'tiempo_calculado_minutos': float(ruta_real['tiempo_total_minutos'] or 15),
                    'calles_utilizadas': ruta_real['calles_utilizadas'] or ['Conesa', 'Zapiola'],
                    'tipos_vias': ruta_real['tipos_vias'] or ['residential'],
                    'precision': 'routing_real_con_coordenadas',
                    
                    # 🎯 COORDENADAS PARA EL MAPA
                    'geometria_completa': {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coordenadas_completas
                        },
                        "properties": {
                            "algoritmo": "pgRouting_Dijkstra",
                            "puntos_totales": len(coordenadas_completas)
                        }
                    },
                    'coordenadas_array': coordenadas_completas,
                    'puntos_totales': len(coordenadas_completas)
                }
                
                logger.info(f"🔥 COORDENADAS LIMPIAS: {len(coordenadas_completas)} puntos totales")
                eta_final = int(ruta_real['tiempo_total_minutos'] or 15)
                
            else:
                logger.info(f"⚠️ Step 6b: Usando FALLBACK - ruta directa")
                
                distancia_directa = calculate_distance_km(
                    tienda_coords['lat'], tienda_coords['lon'],
                    pedido_data['cliente_lat'], pedido_data['cliente_lon']
                )
                
                # Coordenadas fallback
                coordenadas_fallback = [
                    [tienda_coords['lon'], tienda_coords['lat']],
                    [pedido_data['cliente_lon'], pedido_data['cliente_lat']]
                ]
                
                ruta_termonuclear = {
                    'tipo': 'fallback_directo',
                    'algoritmo': 'euclidiano',
                    'distancia_total_km': distancia_directa,
                    'tiempo_calculado_minutos': max(10, int(distancia_directa * 5)),  # ~12 km/h
                    'calles_utilizadas': ['Ruta directa (pgRouting no disponible)'],
                    'tipos_vias': ['direct'],
                    'precision': 'fallback_con_coordenadas',
                    
                    # Coordenadas fallback para el mapa
                    'geometria_completa': {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coordenadas_fallback
                        }
                    },
                    'coordenadas_array': coordenadas_fallback,
                    'puntos_totales': 2
                }
                
                eta_final = max(10, int(distancia_directa * 5))
            
            # 7. RESPUESTA FINAL
            logger.info(f"✅ Step 7: Generando respuesta final...")
            
            tracking_response = TrackingInfo(
                pedido_id=pedido_id,
                status="completed_con_coordenadas",
                rider=RiderInfo(
                    id=1,
                    nombre="Carlos Delivery",
                    lat=tienda_coords['lat'],
                    lon=tienda_coords['lon'],
                    h3_actual="881f1a4a2ffffff",
                    status="ocupado",
                    pedidos_activos=1,
                    tiene_pedido_cerca_local=True,
                    eficiencia_score=85.0
                ),
                ubicacion_actual={
                    "lat": tienda_coords['lat'],
                    "lon": tienda_coords['lon']
                },
                eta_minutos=eta_final,
                ruta_calculada={
                    'tienda': tienda_coords,
                    'cliente': {
                        'lat': pedido_data['cliente_lat'],
                        'lon': pedido_data['cliente_lon'],
                        'nombre': pedido_data['cliente_nombre'],
                        'direccion': pedido_data['cliente_direccion']
                    },
                    'ruta': ruta_termonuclear,
                    'calculado_con': 'API_COMPLETA_CON_COORDENADAS'
                },
                es_batch=False,
                progreso_porcentaje=100
            )
            
            logger.info(f"🚀 Step 7 FINAL: Tracking generado exitosamente con {ruta_termonuclear.get('puntos_totales', 0)} puntos")
            return tracking_response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 ERROR GENERAL en tracking: {e}")
        
        # FALLBACK TOTAL
        return TrackingInfo(
            pedido_id=pedido_id,
            status="error_completo",
            rider=None,
            ubicacion_actual=None,
            eta_minutos=None,
            ruta_calculada={
                'error': str(e),
                'debug_info': 'Revisar logs para más detalles'
            },
            es_batch=False,
            progreso_porcentaje=0
        )
    finally:
        db_conn.close()

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcular distancia euclidiana aproximada en km"""
    dlat = (lat2 - lat1) * 111  # 1° lat ≈ 111 km
    dlon = (lon2 - lon1) * 111 * math.cos(math.radians(lat1))  # Corrección latitud
    
    distance_km = math.sqrt(dlat**2 + dlon**2)
    return round(distance_km, 2)

@app.get("/api/metricas", response_model=MetricasResponse)
async def get_metricas_sistema(db_conn = Depends(get_db_connection)):
    """Obtener métricas del sistema en tiempo real"""
    logger.info("📊 Consultando métricas del sistema")
    
    # Demo metrics
    metricas = MetricasResponse(
        riders_online=4,
        pedidos_activos=2,
        entregas_hoy=15,
        tiempo_promedio_minutos=22.5,
        eficiencia_batching=35.0,
        h3_mas_demandado="881f1a4a2ffffff",
        timestamp=datetime.now()
    )
    
    db_conn.close()
    return metricas

# ENDPOINT FIXED - SIN Field() en parámetros
@app.post("/api/rider/{rider_id}/ubicacion")
async def actualizar_ubicacion_rider(
    rider_id: int,
    ubicacion: RiderUbicacionRequest,  # ← USANDO PYDANTIC MODEL
    db_conn = Depends(get_db_connection)
):
    """Actualizar ubicación de rider (para simulación)"""
    logger.info(f"📍 Actualizando ubicación rider {rider_id}: {ubicacion.lat}, {ubicacion.lon}")
    
    try:
        h3_actual = h3.geo_to_h3(ubicacion.lat, ubicacion.lon, 9)
        
        # Demo response
        result = {
            "status": "updated",
            "rider_id": rider_id,
            "h3_actual": h3_actual,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Ubicación actualizada: H3 {h3_actual}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error actualizando ubicación: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db_conn.close()

@app.post("/api/airflow/trigger")
async def trigger_airflow_manual(
    pedido_id: str,
    rider_id: Optional[int] = None,
    h3_destino: Optional[str] = None
):
    """Trigger MANUAL de DAG Airflow (solo para testing)"""
    logger.info(f"🌊 Trigger Airflow manual: {pedido_id}")
    
    mock_pedido_data = {
        "pedido_id": pedido_id,
        "cliente_nombre": "Test Cliente",
        "cliente_direccion": "Test Address", 
        "pedido_total": 25000,
        "pedido_items": [{"item_nombre": "Test Item", "item_precio": 25000}]
    }
    
    # Usar la función interna
    await trigger_airflow_dag_internal(mock_pedido_data)
    
    return {
        "status": "triggered",
        "dag_run_id": f"rutia_{pedido_id.lower()}",
        "pedido_id": pedido_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/debug/setup-riders")
async def setup_riders_demo(db_conn = Depends(get_db_connection)):
    """Setup riders demo para testing"""
    logger.info("🛵 Setup riders demo")
    
    try:
        motor = get_motor_espacial()
        riders_data = motor.generar_posiciones_riders_relativas()
        motor.close()
        
        with db_conn.cursor() as cursor:
            # Clear existing riders
            cursor.execute("DELETE FROM riders;")
            
            # Insert demo riders
            for i, rider in enumerate(riders_data):
                query = """
                INSERT INTO riders (
                    nombre, telefono, ubicacion_actual, h3_actual, 
                    h3_cobertura, tiene_pedido_cerca_local, pedidos_activos, status, eficiencia_score
                ) VALUES (%s, %s, ST_Point(%s, %s), %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(query, (
                    rider['nombre'], rider['telefono'],
                    rider['lon'], rider['lat'], rider['h3_actual'],
                    rider['h3_cobertura'], rider['tiene_pedido_cerca_local'],
                    rider['pedidos_activos'], rider['status'], 50.0 + (i * 10)
                ))
            
            db_conn.commit()
        
        logger.info(f"🛵 {len(riders_data)} riders demo creados")
        return {"status": "created", "riders": len(riders_data)}
        
    except Exception as e:
        logger.error(f"❌ Error setup riders: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db_conn.close()

@app.get("/api/debug/test-ruta-real/{pedido_id}")
async def test_ruta_real_debug(
    pedido_id: str,
    db_conn = Depends(get_db_connection)
):
    """🔧 DEBUG: Test para ver datos reales de ruta en PostgreSQL"""
    logger.info(f"🔧 DEBUG: Testeando ruta real para {pedido_id}")
    
    try:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            
            # 1. Info del pedido
            cursor.execute("""
                SELECT 
                    pedido_externo_id, cliente_nombre, cliente_direccion,
                    h3_destino, status, tiempo_estimado_minutos
                FROM pedidos 
                WHERE pedido_externo_id = %s;
            """, (pedido_id,))
            
            pedido_debug = cursor.fetchone()
            
            # 2. Calles OSM para este pedido
            if pedido_debug and pedido_debug['h3_destino']:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_calles,
                        SUM(longitud_km) as distancia_total,
                        ARRAY_AGG(DISTINCT nombre) as calles_nombres,
                        ARRAY_AGG(DISTINCT tipo_highway) as tipos_vias
                    FROM osm_calles_routing 
                    WHERE h3_hexagon = %s;
                """, (pedido_debug['h3_destino'],))
                
                calles_debug = cursor.fetchone()
            else:
                calles_debug = None
            
            # 3. Todas las calles disponibles
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_calles_sistema,
                    COUNT(DISTINCT h3_hexagon) as hexagonos_unicos
                FROM osm_calles_routing;
            """)
            
            sistema_debug = cursor.fetchone()
            
            debug_result = {
                "pedido_encontrado": pedido_debug is not None,
                "pedido_info": dict(pedido_debug) if pedido_debug else None,
                "calles_para_pedido": dict(calles_debug) if calles_debug else None,
                "sistema_info": dict(sistema_debug) if sistema_debug else None,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🔧 DEBUG completado para {pedido_id}")
            return debug_result
            
    except Exception as e:
        logger.error(f"❌ Error en debug: {e}")
        return {"error": str(e), "pedido_id": pedido_id}
    finally:
        db_conn.close()

# =============================================================================
# EVENTOS DE INICIO Y CIERRE
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Eventos al iniciar la aplicación"""
    logger.info("🚀 RutIA API iniciando...")
    logger.info("🗺️ RutIA API lista para procesar pedidos inteligentes")

@app.on_event("shutdown")
async def shutdown_event():
    """Eventos al cerrar la aplicación"""
    logger.info("🔌 RutIA API cerrando conexiones...")
    logger.info("✅ RutIA API cerrada correctamente")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=3000, 
        reload=True,
        log_level="info"
    )