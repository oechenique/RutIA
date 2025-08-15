"""
🗄️ RutIA Database Utilities
Conexiones y operaciones PostgreSQL/PostGIS para el pipeline termonuclear
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, List, Tuple, Any, Optional
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manager para todas las operaciones de base de datos"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'rutia_db'),
            'user': os.getenv('POSTGRES_USER', 'rutia_admin'),
            'password': os.getenv('POSTGRES_PASSWORD', 'espacial123')
        }
    
    def get_connection(self):
        """Obtener conexión a PostgreSQL"""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            logger.error(f"❌ Error conectando a DB: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False) -> Any:
        """Ejecutar query con manejo de errores"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error ejecutando query: {e}")
            raise
        finally:
            conn.close()
    
    def insert_pedido(self, pedido_data: Dict) -> int:
        """Insertar pedido en base de datos"""
        query = """
            INSERT INTO pedidos (
                pedido_externo_id, cliente_nombre, cliente_direccion,
                items, descripcion_items, precio_total, status,
                coordenadas_entrega, h3_destino
            ) VALUES (%s, %s, %s, %s, %s, %s, 'procesando_espacial',
                     ST_Point(0, 0), 'pending_geocoding')
            RETURNING id
        """
        
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    pedido_data['pedido_id'],
                    pedido_data['cliente_nombre'],
                    pedido_data['cliente_direccion'], 
                    json.dumps(pedido_data.get('pedido_items', [])),
                    f"Pedido termonuclear: {len(pedido_data.get('pedido_items', []))} items",
                    pedido_data.get('pedido_total', 0)
                ))
                pedido_id = cursor.fetchone()[0]
                conn.commit()
                return pedido_id
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error insertando pedido: {e}")
            raise
        finally:
            conn.close()
    
    def create_osm_routing_table(self):
        """Crear tabla para calles OSM routing"""
        query = """
            CREATE TABLE IF NOT EXISTS osm_calles_routing (
                id SERIAL PRIMARY KEY,
                osm_way_id BIGINT,
                nombre VARCHAR(255),
                tipo_highway VARCHAR(50),
                geometria GEOMETRY(LINESTRING, 4326),
                longitud_km DECIMAL(8, 3),
                source_node INTEGER,
                target_node INTEGER,
                cost DECIMAL(8, 3),
                reverse_cost DECIMAL(8, 3),
                h3_hexagon VARCHAR(15),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- Índices espaciales para routing
            CREATE INDEX IF NOT EXISTS idx_osm_calles_geom 
            ON osm_calles_routing USING GIST(geometria);
            
            CREATE INDEX IF NOT EXISTS idx_osm_calles_source 
            ON osm_calles_routing(source_node);
            
            CREATE INDEX IF NOT EXISTS idx_osm_calles_target 
            ON osm_calles_routing(target_node);
            
            CREATE INDEX IF NOT EXISTS idx_osm_calles_h3 
            ON osm_calles_routing(h3_hexagon);
        """
        
        self.execute_query(query)
        logger.info("✅ Tabla osm_calles_routing creada/verificada")
    
    def clear_routing_table(self):
        """Limpiar tabla de routing para nuevo pedido"""
        self.execute_query("TRUNCATE TABLE osm_calles_routing RESTART IDENTITY")
        logger.info("🧹 Tabla routing limpiada")
    
    def insert_osm_ways(self, osm_ways: List[Dict], h3_hexagon: str) -> int:
        """Insertar ways OSM en la tabla de routing"""
        if not osm_ways:
            return 0
        
        conn = self.get_connection()
        inserted_count = 0
        
        try:
            with conn.cursor() as cursor:
                for way in osm_ways:
                    try:
                        # Crear LineString de geometría
                        coords = way.get('geometry', [])
                        if len(coords) < 2:
                            continue
                        
                        linestring_coords = [(coord['lon'], coord['lat']) for coord in coords]
                        linestring_wkt = f"LINESTRING({', '.join([f'{lon} {lat}' for lon, lat in linestring_coords])})"
                        
                        # Calcular longitud y costo
                        longitud_km = self._calculate_way_length(coords)
                        highway_type = way['tags'].get('highway', 'residential')
                        cost = self._calculate_cost(longitud_km, highway_type)
                        
                        cursor.execute("""
                            INSERT INTO osm_calles_routing (
                                osm_way_id, nombre, tipo_highway, geometria, 
                                longitud_km, cost, reverse_cost, h3_hexagon
                            ) VALUES (
                                %s, %s, %s, ST_GeomFromText(%s, 4326),
                                %s, %s, %s, %s
                            )
                        """, (
                            way['id'],
                            way['tags'].get('name', f'Calle {way["id"]}'),
                            highway_type,
                            linestring_wkt,
                            longitud_km,
                            cost,
                            cost,  # reverse_cost igual
                            h3_hexagon
                        ))
                        
                        inserted_count += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Error insertando way {way.get('id', 'unknown')}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error insertando OSM ways: {e}")
            raise
        finally:
            conn.close()
        
        return inserted_count
    
    def _calculate_way_length(self, coords: List[Dict]) -> float:
        """Calcular longitud aproximada de un way"""
        if len(coords) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(len(coords) - 1):
            # Cálculo aproximado usando distancia euclidiana
            lat1, lon1 = coords[i]['lat'], coords[i]['lon']
            lat2, lon2 = coords[i+1]['lat'], coords[i+1]['lon']
            
            # Conversión aproximada a km (1 grado ≈ 111 km)
            dlat = (lat2 - lat1) * 111
            dlon = (lon2 - lon1) * 111 * abs(lat1 / 90)  # Corrección por latitud
            
            segment_length = (dlat**2 + dlon**2)**0.5
            total_length += segment_length
        
        return total_length
    
    def _calculate_cost(self, longitud_km: float, highway_type: str) -> float:
        """Calcular costo (tiempo en minutos) basado en tipo de calle"""
        speed_map = {
            'primary': 50,
            'secondary': 40, 
            'tertiary': 30,
            'residential': 25,
            'unclassified': 20,
            'living_street': 15,
            'trunk': 60
        }
        
        speed_kmh = speed_map.get(highway_type, 25)
        return (longitud_km / speed_kmh) * 60  # Minutos
    
    def prepare_pgrouting_topology(self) -> bool:
        """Preparar topology para pgRouting - FIXED"""
        try:
            queries = [
                # 1. Asegurar que pgrouting existe
                "CREATE EXTENSION IF NOT EXISTS pgrouting;",
                
                # 2. Agregar columnas source/target si no existen
                """
                ALTER TABLE osm_calles_routing 
                ADD COLUMN IF NOT EXISTS source INTEGER;
                """,
                """
                ALTER TABLE osm_calles_routing 
                ADD COLUMN IF NOT EXISTS target INTEGER;
                """,
                
                # 3. Crear topology REAL - ESTE ES EL FIX
                """
                SELECT pgr_createTopology('osm_calles_routing', 0.00001, 'geometria', 'id', 'source', 'target', clean := true);
                """,
                
                # 4. Analizar topology para ver si funcionó
                """
                SELECT pgr_analyzeGraph('osm_calles_routing', 0.00001, 'geometria', 'id', 'source', 'target');
                """
            ]
            
            for query in queries:
                logger.info(f"🔧 Ejecutando: {query[:50]}...")
                self.execute_query(query)
            
            # 5. VERIFICAR que se creó la tabla vertices
            result = self.execute_query("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'osm_calles_routing_vertices_pgr'
                );
            """, fetch=True)
            
            if result and result[0]['exists']:
                logger.info("✅ Topology pgRouting creada exitosamente")
                
                # Contar nodos
                count_result = self.execute_query("""
                    SELECT COUNT(*) as total_nodes FROM osm_calles_routing_vertices_pgr;
                """, fetch=True)
                
                if count_result:
                    logger.info(f"🔗 Nodos creados: {count_result[0]['total_nodes']}")
                    
                return True
            else:
                logger.error("❌ Tabla vertices_pgr NO se creó")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error preparando topology: {e}")
            return False
    
    def find_closest_node(self, lat: float, lon: float) -> Optional[int]:
        """Encontrar nodo más cercano para routing"""
        query = """
            SELECT id as node_id, 
                   ST_Distance(the_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as distance
            FROM osm_calles_routing_vertices_pgr 
            ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1;
        """
        
        try:
            result = self.execute_query(query, (lon, lat, lon, lat), fetch=True)
            if result:
                return result[0]['node_id']
            return None
        except Exception as e:
            logger.error(f"❌ Error buscando nodo más cercano: {e}")
            return None
    
    def calculate_dijkstra_route(self, source_node: int, target_node: int) -> List[Dict]:
        """Calcular ruta usando Dijkstra"""
        query = """
            SELECT r.seq, r.path_seq, r.node, r.edge, r.cost, r.agg_cost,
                   e.geometria, e.nombre, e.tipo_highway, e.longitud_km
            FROM pgr_dijkstra(
                'SELECT id, source, target, cost, reverse_cost FROM osm_calles_routing',
                %s, %s, false
            ) AS r
            LEFT JOIN osm_calles_routing e ON (r.edge = e.id)
            ORDER BY r.path_seq;
        """
        
        try:
            return self.execute_query(query, (source_node, target_node), fetch=True)
        except Exception as e:
            logger.error(f"❌ Error calculando ruta Dijkstra: {e}")
            return []
    
    def update_pedido_final(self, pedido_id: str, rider_id: int, eta_minutos: int, 
                           cliente_lat: float, cliente_lon: float, cliente_h3: str):
        """Actualizar pedido con información final"""
        query = """
            UPDATE pedidos 
            SET status = 'termonuclear_completed',
                coordenadas_entrega = ST_Point(%s, %s),
                h3_destino = %s,
                tiempo_estimado_minutos = %s,
                rider_id = %s,
                updated_at = NOW()
            WHERE pedido_externo_id = %s
        """
        
        self.execute_query(query, (
            cliente_lon, cliente_lat, cliente_h3, 
            eta_minutos, rider_id, pedido_id
        ))
        
        logger.info(f"✅ Pedido {pedido_id} actualizado - ETA: {eta_minutos} min")


# Instancia global para usar en tasks
db_manager = DatabaseManager()
