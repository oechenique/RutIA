"""
RutIA - Motor de Análisis Espacial
Motor principal para procesamiento geoespacial inteligente

Funciones principales:
- Geocoding inteligente con fallbacks
- Búsqueda de riders óptimos con H3
- Cálculo de eficiencia de batching
- Extracción de área OSM para routing
"""

import os
import h3
import requests
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmpresaConfig:
    """Configuración de la empresa desde .env"""
    nombre: str
    direccion: str
    lat: float
    lon: float
    h3_location: str
    h3_resolution: int = 9

@dataclass
class RiderResult:
    """Resultado de búsqueda de rider"""
    id: int
    nombre: str
    telefono: str
    h3_actual: str
    lat: float
    lon: float
    distancia_hexs: int
    tiene_pedido_cerca_local: bool
    eficiencia_score: float

@dataclass
class BatchingResult:
    """Resultado de análisis de batching"""
    es_posible: bool
    pedido_existente_id: Optional[int]
    distancia_hexs: int
    ahorro_estimado_minutos: float
    eficiencia_ganada: float

class RutIASpatialEngine:
    """
    Motor espacial principal de RutIA
    Maneja todas las operaciones geoespaciales del sistema
    """
    
    def __init__(self):
        """Inicializar motor espacial con configuración"""
        self.empresa_config = self._load_empresa_config()
        self.db_connection = self._get_db_connection()
        logger.info(f"🗺️ RutIA Motor Espacial iniciado para {self.empresa_config.nombre}")
    
    def _load_empresa_config(self) -> EmpresaConfig:
        """Cargar configuración de empresa desde .env"""
        try:
            lat = float(os.getenv('EMPRESA_LAT', -34.6037))
            lon = float(os.getenv('EMPRESA_LON', -58.3816))
            h3_res = int(os.getenv('H3_RESOLUTION', 9))
            
            # Calcular H3 de la empresa
            h3_location = h3.geo_to_h3(lat, lon, h3_res)
            
            return EmpresaConfig(
                nombre=os.getenv('EMPRESA_NOMBRE', 'RutIA Demo'),
                direccion=os.getenv('EMPRESA_DIRECCION', 'Ubicación no configurada'),
                lat=lat,
                lon=lon,
                h3_location=h3_location,
                h3_resolution=h3_res
            )
        except Exception as e:
            logger.error(f"❌ Error cargando configuración empresa: {e}")
            raise
    
    def _get_db_connection(self):
        """Obtener conexión a PostgreSQL/PostGIS"""
        try:
            connection = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                database=os.getenv('POSTGRES_DB', 'rutia_db'),
                user=os.getenv('POSTGRES_USER', 'rutia_admin'),
                password=os.getenv('POSTGRES_PASSWORD', 'espacial123')
            )
            return connection
        except Exception as e:
            logger.error(f"❌ Error conectando a base de datos: {e}")
            raise
    
    def geocoding_inteligente(self, direccion: str) -> Tuple[float, float]:
        """
        Geocoding inteligente con múltiples providers y fallbacks
        
        Args:
            direccion: Dirección a geocodificar
            
        Returns:
            Tuple[lat, lon]: Coordenadas geocodificadas
        """
        logger.info(f"📍 Geocodificando: {direccion}")
        
        # Provider 1: Nominatim (OpenStreetMap)
        try:
            coords = self._geocode_nominatim(direccion)
            if coords:
                logger.info(f"✅ Geocoding exitoso con Nominatim: {coords}")
                return coords
        except Exception as e:
            logger.warning(f"⚠️ Nominatim falló: {e}")
        
        # Provider 2: Fallback a coordenadas empresa si falla
        logger.warning(f"🔄 Usando coordenadas empresa como fallback")
        return (self.empresa_config.lat, self.empresa_config.lon)
    
    def _geocode_nominatim(self, direccion: str) -> Optional[Tuple[float, float]]:
        """Geocoding usando Nominatim (OSM)"""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': direccion,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'ar',  # Priorizar Argentina
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'RutIA-GeoDojo/1.0 (hello@geodojo.ai)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return (lat, lon)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error en Nominatim: {e}")
            return None
    
    def buscar_rider_optimo(self, h3_destino: str) -> Optional[RiderResult]:
        """
        Buscar rider óptimo usando inteligencia espacial H3
        Prioriza riders con pedidos cerca del local (batching)
        
        Args:
            h3_destino: Hexágono H3 del destino del cliente
            
        Returns:
            RiderResult: Datos del rider óptimo encontrado
        """
        logger.info(f"🛵 Buscando rider óptimo para H3: {h3_destino}")
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Query inteligente con scoring por batching
                query = """
                WITH riders_disponibles AS (
                    SELECT 
                        r.id,
                        r.nombre,
                        r.telefono,
                        r.h3_actual,
                        ST_Y(r.ubicacion_actual) as lat,
                        ST_X(r.ubicacion_actual) as lon,
                        r.tiene_pedido_cerca_local,
                        r.pedidos_activos,
                        -- Calcular distancia en hexágonos
                        CASE 
                            WHEN r.h3_actual = %s THEN 0
                            ELSE (
                                SELECT COUNT(*) 
                                FROM generate_series(1, 10) i 
                                WHERE %s = ANY(
                                    SELECT h3_hex_ring(r.h3_actual, i)
                                )
                            )
                        END as distancia_hexs
                    FROM riders r
                    WHERE r.status = 'disponible'
                      AND r.pedidos_activos < 3
                      AND %s = ANY(r.h3_cobertura)
                ),
                riders_con_scoring AS (
                    SELECT *,
                        -- Scoring inteligente: prioriza batching
                        CASE 
                            WHEN tiene_pedido_cerca_local THEN 100.0 - (distancia_hexs * 5)
                            ELSE 50.0 - (distancia_hexs * 10) - (pedidos_activos * 15)
                        END as eficiencia_score
                    FROM riders_disponibles
                    WHERE distancia_hexs <= 5  -- Máximo 5 hexágonos de distancia
                )
                SELECT * FROM riders_con_scoring 
                ORDER BY eficiencia_score DESC, distancia_hexs ASC
                LIMIT 1;
                """
                
                cursor.execute(query, (h3_destino, h3_destino, h3_destino))
                result = cursor.fetchone()
                
                if result:
                    rider = RiderResult(
                        id=result['id'],
                        nombre=result['nombre'],
                        telefono=result['telefono'],
                        h3_actual=result['h3_actual'],
                        lat=result['lat'],
                        lon=result['lon'],
                        distancia_hexs=result['distancia_hexs'],
                        tiene_pedido_cerca_local=result['tiene_pedido_cerca_local'],
                        eficiencia_score=result['eficiencia_score']
                    )
                    
                    logger.info(f"✅ Rider encontrado: {rider.nombre} (Score: {rider.eficiencia_score:.1f})")
                    return rider
                else:
                    logger.warning("⚠️ No se encontró rider disponible")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error buscando rider: {e}")
            return None
    
    def calcular_batching_opportunity(self, rider_id: int, h3_destino: str) -> BatchingResult:
        """
        Calcular oportunidad de batching para un rider
        
        Args:
            rider_id: ID del rider
            h3_destino: H3 destino del nuevo pedido
            
        Returns:
            BatchingResult: Análisis de oportunidad de batching
        """
        logger.info(f"🔄 Calculando batching para rider {rider_id}, destino {h3_destino}")
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Buscar pedidos activos del rider cerca del destino
                query = """
                SELECT 
                    p.id,
                    p.h3_destino,
                    -- Calcular distancia entre hexágonos
                    CASE 
                        WHEN p.h3_destino = %s THEN 0
                        ELSE (
                            SELECT MIN(i) 
                            FROM generate_series(1, 5) i 
                            WHERE %s = ANY(
                                SELECT h3_hex_ring(p.h3_destino, i)
                            )
                        )
                    END as distancia_hexs,
                    p.tiempo_estimado
                FROM pedidos p
                WHERE p.rider_id = %s 
                  AND p.status IN ('asignado', 'en_camino')
                ORDER BY distancia_hexs ASC NULLS LAST
                LIMIT 1;
                """
                
                cursor.execute(query, (h3_destino, h3_destino, rider_id))
                result = cursor.fetchone()
                
                if result and result['distancia_hexs'] is not None and result['distancia_hexs'] <= 2:
                    # Hay oportunidad de batching (hexágonos adyacentes o cercanos)
                    ahorro_estimado = self._calcular_ahorro_batching(result['distancia_hexs'])
                    eficiencia_ganada = min(0.8, 0.3 + (0.1 * (3 - result['distancia_hexs'])))
                    
                    batching = BatchingResult(
                        es_posible=True,
                        pedido_existente_id=result['id'],
                        distancia_hexs=result['distancia_hexs'],
                        ahorro_estimado_minutos=ahorro_estimado,
                        eficiencia_ganada=eficiencia_ganada
                    )
                    
                    logger.info(f"✅ Batching posible: ahorro {ahorro_estimado:.1f} min, eficiencia +{eficiencia_ganada:.1%}")
                    return batching
                else:
                    return BatchingResult(
                        es_posible=False,
                        pedido_existente_id=None,
                        distancia_hexs=999,
                        ahorro_estimado_minutos=0.0,
                        eficiencia_ganada=0.0
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error calculando batching: {e}")
            return BatchingResult(False, None, 999, 0.0, 0.0)
    
    def _calcular_ahorro_batching(self, distancia_hexs: int) -> float:
        """Calcular ahorro estimado en minutos por batching"""
        if distancia_hexs == 0:
            return 15.0  # Mismo hexágono = máximo ahorro
        elif distancia_hexs == 1:
            return 10.0  # Hexágonos adyacentes
        elif distancia_hexs == 2:
            return 5.0   # Cerca
        else:
            return 0.0   # Muy lejos, no vale la pena
    
    def extraer_area_osm_h3(self, h3_hexagons: List[str]) -> Dict[str, Any]:
        """
        Extraer red vial OSM del área definida por hexágonos H3
        
        Args:
            h3_hexagons: Lista de hexágonos H3 del área
            
        Returns:
            Dict con información de calles OSM para routing
        """
        logger.info(f"🗺️ Extrayendo calles OSM para {len(h3_hexagons)} hexágonos")
        
        try:
            # Calcular bounding box del área H3
            bbox = self._calcular_bbox_h3_area(h3_hexagons)
            
            # Query Overpass API para calles
            overpass_query = self._construir_overpass_query(bbox)
            
            # Ejecutar query
            osm_data = self._ejecutar_overpass_query(overpass_query)
            
            if osm_data:
                logger.info(f"✅ OSM: {len(osm_data.get('elements', []))} elementos obtenidos")
                return {
                    'bbox': bbox,
                    'elements': osm_data.get('elements', []),
                    'hexagons_covered': h3_hexagons,
                    'timestamp': osm_data.get('generator', 'unknown')
                }
            else:
                logger.warning("⚠️ No se obtuvieron datos OSM")
                return {'elements': [], 'bbox': bbox}
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo OSM: {e}")
            return {'elements': [], 'error': str(e)}
    
    def _calcular_bbox_h3_area(self, h3_hexagons: List[str]) -> Dict[str, float]:
        """Calcular bounding box de un área H3"""
        all_coords = []
        
        for h3_hex in h3_hexagons:
            # Obtener vértices del hexágono
            boundary = h3.h3_to_geo_boundary(h3_hex, geo_json=True)
            all_coords.extend(boundary)
        
        if not all_coords:
            return {}
        
        lats = [coord[1] for coord in all_coords]
        lons = [coord[0] for coord in all_coords]
        
        # Expandir bbox un poco para incluir calles conectoras
        buffer = 0.005  # ~500m aproximadamente
        
        return {
            'south': min(lats) - buffer,
            'north': max(lats) + buffer,
            'west': min(lons) - buffer,
            'east': max(lons) + buffer
        }
    
    def _construir_overpass_query(self, bbox: Dict[str, float]) -> str:
        """Construir query Overpass para extraer calles"""
        return f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(primary|secondary|tertiary|residential|trunk|unclassified)$"]
             ({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"="living_street"]
             ({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
    
    def _ejecutar_overpass_query(self, query: str) -> Optional[Dict]:
        """Ejecutar query contra Overpass API"""
        try:
            url = os.getenv('OSM_API_URL', 'https://overpass-api.de/api/interpreter')
            
            headers = {
                'User-Agent': 'RutIA-GeoDojo/1.0 (hello@geodojo.ai)'
            }
            
            response = requests.post(
                url, 
                data=query, 
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ Error en Overpass API: {e}")
            return None
    
    def calcular_h3_cobertura_rider(self, h3_center: str, radio_hexs: int = 3) -> List[str]:
        """
        Calcular área de cobertura H3 para un rider
        
        Args:
            h3_center: Hexágono central del rider
            radio_hexs: Radio en hexágonos
            
        Returns:
            Lista de hexágonos que puede cubrir
        """
        logger.info(f"🔶 Calculando cobertura H3 desde {h3_center}, radio {radio_hexs}")
        
        try:
            cobertura = [h3_center]  # Incluir hexágono central
            
            # Agregar anillos concéntricos
            for k in range(1, radio_hexs + 1):
                ring = h3.hex_ring(h3_center, k)
                cobertura.extend(ring)
            
            logger.info(f"✅ Cobertura calculada: {len(cobertura)} hexágonos")
            return cobertura
            
        except Exception as e:
            logger.error(f"❌ Error calculando cobertura H3: {e}")
            return [h3_center]  # Fallback al hexágono central
    
    def generar_posiciones_riders_relativas(self) -> List[Dict[str, Any]]:
        """
        Generar posiciones relativas de riders respecto a la empresa
        Para demo y testing
        
        Returns:
            Lista de riders con posiciones H3 relativas
        """
        logger.info("🛵 Generando posiciones relativas de riders")
        
        empresa_h3 = self.empresa_config.h3_location
        riders_data = []
        
        # Configuración de riders demo
        riders_config = [
            {
                'nombre': 'Carlos', 
                'offset_hexs': 2, 
                'tiene_pedido_cerca': True,
                'telefono': '+5491234567890'
            },
            {
                'nombre': 'María', 
                'offset_hexs': 3, 
                'tiene_pedido_cerca': False,
                'telefono': '+5491234567891'
            },
            {
                'nombre': 'Juan', 
                'offset_hexs': 1, 
                'tiene_pedido_cerca': False,
                'telefono': '+5491234567892'
            },
            {
                'nombre': 'Ana', 
                'offset_hexs': 4, 
                'tiene_pedido_cerca': False,
                'telefono': '+5491234567893'
            }
        ]
        
        for i, config in enumerate(riders_config):
            try:
                # Calcular posición H3 relativa
                neighbors = h3.hex_ring(empresa_h3, config['offset_hexs'])
                if neighbors:
                    rider_h3 = neighbors[i % len(neighbors)]  # Distribuir en el anillo
                else:
                    rider_h3 = empresa_h3
                
                # Convertir H3 a coordenadas
                lat, lon = h3.h3_to_geo(rider_h3)
                
                # Calcular cobertura
                cobertura = self.calcular_h3_cobertura_rider(rider_h3, 3)
                
                rider_data = {
                    'id': i + 1,
                    'nombre': config['nombre'],
                    'telefono': config['telefono'],
                    'lat': lat,
                    'lon': lon,
                    'h3_actual': rider_h3,
                    'h3_cobertura': cobertura,
                    'tiene_pedido_cerca_local': config['tiene_pedido_cerca'],
                    'pedidos_activos': 1 if config['tiene_pedido_cerca'] else 0,
                    'status': 'disponible'
                }
                
                riders_data.append(rider_data)
                
            except Exception as e:
                logger.error(f"❌ Error generando rider {config['nombre']}: {e}")
        
        logger.info(f"✅ {len(riders_data)} riders generados")
        return riders_data
    
    def close(self):
        """Cerrar conexiones"""
        if self.db_connection:
            self.db_connection.close()
            logger.info("🔌 Conexión DB cerrada")

# Funciones de utilidad para uso externo
def crear_motor_espacial() -> RutIASpatialEngine:
    """Factory function para crear motor espacial"""
    return RutIASpatialEngine()

def calcular_tiempo_estimado_h3(h3_origen: str, h3_destino: str) -> int:
    """
    Calcular tiempo estimado entre dos hexágonos H3
    Función simplificada para demos
    
    Args:
        h3_origen: Hexágono origen
        h3_destino: Hexágono destino
        
    Returns:
        Tiempo estimado en minutos
    """
    try:
        # Calcular distancia en hexágonos
        distancia_hexs = h3.h3_distance(h3_origen, h3_destino)
        
        # Aproximación: cada hexágono = 2 minutos (velocidad promedio urbana)
        tiempo_base = distancia_hexs * 2
        
        # Tiempo mínimo 5 min, máximo 45 min
        tiempo_estimado = max(5, min(45, tiempo_base + 5))
        
        return tiempo_estimado
        
    except Exception:
        return 20  # Fallback por defecto

# Test de funcionalidades principales
if __name__ == "__main__":
    print("🗺️ RutIA - Test Motor Espacial")
    
    try:
        # Crear motor
        motor = crear_motor_espacial()
        
        # Test geocoding
        coords = motor.geocoding_inteligente("Blanco Encalada 2680, CABA")
        print(f"📍 Geocoding: {coords}")
        
        # Test H3
        h3_destino = h3.geo_to_h3(coords[1], coords[0], 9)
        print(f"🔶 H3 destino: {h3_destino}")
        
        # Test riders
        riders = motor.generar_posiciones_riders_relativas()
        print(f"🛵 Riders generados: {len(riders)}")
        
        # Cleanup
        motor.close()
        
        print("✅ Test completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error en test: {e}")