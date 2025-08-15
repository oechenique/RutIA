"""
🔶 RutIA H3 Utilities  
Sistema hexagonal H3 compatible para análisis espacial termonuclear
"""

import h3
import random
import logging
from typing import List, Dict, Tuple, Optional
import math

logger = logging.getLogger(__name__)

class H3SpatialEngine:
    """Engine para operaciones H3 con compatibilidad de versiones"""
    
    def __init__(self, resolution: int = 9):
        self.resolution = resolution
        self.approx_hex_radius_m = self._get_hex_radius(resolution)
    
    def _get_hex_radius(self, resolution: int) -> float:
        """Radio aproximado del hexágono por resolución"""
        radius_map = {
            7: 1220,   # ~1.2km
            8: 460,    # ~460m  
            9: 174,    # ~174m (nuestro target)
            10: 66,    # ~66m
            11: 25     # ~25m
        }
        return radius_map.get(resolution, 174)
    
    def latlng_to_h3(self, lat: float, lon: float) -> Optional[str]:
        """Convertir coordenadas a H3 (compatible)"""
        try:
            if hasattr(h3, 'latlng_to_cell'):
                return h3.latlng_to_cell(lat, lon, self.resolution)
            elif hasattr(h3, 'geo_to_h3'):
                return h3.geo_to_h3(lat, lon, self.resolution)
            else:
                logger.error("❌ H3 library method not found")
                return None
        except Exception as e:
            logger.error(f"❌ Error H3 conversion: {e}")
            return None
    
    def h3_to_latlng(self, h3_cell: str) -> Tuple[Optional[float], Optional[float]]:
        """Convertir H3 a coordenadas (compatible)"""
        try:
            if hasattr(h3, 'cell_to_latlng'):
                return h3.cell_to_latlng(h3_cell)
            elif hasattr(h3, 'h3_to_geo'):
                return h3.h3_to_geo(h3_cell)
            else:
                logger.error("❌ H3 library method not found")
                return None, None
        except Exception as e:
            logger.error(f"❌ Error H3 to coordinates: {e}")
            return None, None
    
    def get_k_ring(self, h3_cell: str, k: int) -> List[str]:
        """Obtener anillo de hexágonos (compatible)"""
        try:
            if hasattr(h3, 'k_ring'):
                return list(h3.k_ring(h3_cell, k))
            elif hasattr(h3, 'hex_ring'):
                # Fallback: usar hex_ring para cada nivel
                result = [h3_cell] if k >= 0 else []
                for ring_k in range(1, k + 1):
                    try:
                        ring_hexs = h3.hex_ring(h3_cell, ring_k)
                        result.extend(ring_hexs)
                    except:
                        break
                return result
            else:
                logger.error("❌ H3 k_ring method not found")
                return [h3_cell]
        except Exception as e:
            logger.error(f"❌ Error H3 k_ring: {e}")
            return [h3_cell]
    
    def h3_line(self, start_h3: str, end_h3: str) -> List[str]:
        """Obtener línea H3 entre dos hexágonos (compatible)"""
        try:
            if hasattr(h3, 'grid_path_cells'):
                return list(h3.grid_path_cells(start_h3, end_h3))
            elif hasattr(h3, 'h3_line'):
                return list(h3.h3_line(start_h3, end_h3))
            else:
                # Fallback manual usando aproximación
                return self._manual_h3_line(start_h3, end_h3)
        except Exception as e:
            logger.error(f"❌ Error H3 line: {e}")
            return self._manual_h3_line(start_h3, end_h3)
    
    def _manual_h3_line(self, start_h3: str, end_h3: str) -> List[str]:
        """Aproximar línea H3 manualmente"""
        try:
            # Obtener coordenadas de inicio y fin
            start_lat, start_lon = self.h3_to_latlng(start_h3)
            end_lat, end_lon = self.h3_to_latlng(end_h3)
            
            if not all([start_lat, start_lon, end_lat, end_lon]):
                return [start_h3, end_h3]
            
            # Generar puntos intermedios
            line_hexs = [start_h3]
            steps = max(10, int(self._distance_km(start_lat, start_lon, end_lat, end_lon) * 10))
            
            for i in range(1, steps):
                factor = i / steps
                inter_lat = start_lat + (end_lat - start_lat) * factor
                inter_lon = start_lon + (end_lon - start_lon) * factor
                
                inter_h3 = self.latlng_to_h3(inter_lat, inter_lon)
                if inter_h3 and inter_h3 not in line_hexs:
                    line_hexs.append(inter_h3)
            
            if end_h3 not in line_hexs:
                line_hexs.append(end_h3)
            
            return line_hexs
            
        except Exception as e:
            logger.error(f"❌ Error manual H3 line: {e}")
            return [start_h3, end_h3]
    
    def _distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcular distancia aproximada en km"""
        dlat = (lat2 - lat1) * 111
        dlon = (lon2 - lon1) * 111 * math.cos(math.radians(lat1))
        return math.sqrt(dlat**2 + dlon**2)
    
    def get_hex_boundary(self, h3_cell: str) -> List[Tuple[float, float]]:
        """Obtener boundary del hexágono (compatible)"""
        try:
            if hasattr(h3, 'cell_to_boundary'):
                return list(h3.cell_to_boundary(h3_cell))
            elif hasattr(h3, 'h3_to_geo_boundary'):
                return h3.h3_to_geo_boundary(h3_cell, geo_json=False)
            else:
                # Fallback: aproximar hexágono con centro + radio
                lat, lon = self.h3_to_latlng(h3_cell)
                if lat and lon:
                    return self._approximate_hex_boundary(lat, lon)
                return []
        except Exception as e:
            logger.error(f"❌ Error H3 boundary: {e}")
            lat, lon = self.h3_to_latlng(h3_cell)
            if lat and lon:
                return self._approximate_hex_boundary(lat, lon)
            return []
    
    def _approximate_hex_boundary(self, lat: float, lon: float) -> List[Tuple[float, float]]:
        """Aproximar hexágono usando 6 puntos"""
        radius_deg = self.approx_hex_radius_m / 111000  # Convertir metros a grados
        
        boundary = []
        for i in range(6):
            angle = i * math.pi / 3  # 60 grados por vértice
            vertex_lat = lat + radius_deg * math.cos(angle)
            vertex_lon = lon + radius_deg * math.sin(angle) / math.cos(math.radians(lat))
            boundary.append((vertex_lat, vertex_lon))
        
        return boundary


class RiderManager:
    """Manager para crear y posicionar riders en hexágonos H3"""
    
    def __init__(self, h3_engine: H3SpatialEngine):
        self.h3_engine = h3_engine
    
    def create_riders_around_business(self, business_lat: float, business_lon: float, 
                                    count: int = 4) -> List[Dict]:
        """Crear riders en hexágonos cercanos al negocio"""
        
        business_h3 = self.h3_engine.latlng_to_h3(business_lat, business_lon)
        if not business_h3:
            logger.error("❌ No se pudo obtener H3 del negocio")
            return []
        
        logger.info(f"🏪 Negocio en H3: {business_h3}")
        
        # Obtener hexágonos en anillos 1-3 (2-4 hexágonos de distancia)
        available_positions = []
        
        for k in range(2, 5):  # k=2,3,4 (aprox 400m, 600m, 800m)
            ring_hexs = self.h3_engine.get_k_ring(business_h3, k)
            # Filtrar solo los del anillo actual (no anteriores)
            if k > 2:
                previous_hexs = self.h3_engine.get_k_ring(business_h3, k-1)
                ring_hexs = [h for h in ring_hexs if h not in previous_hexs]
            
            available_positions.extend([(h, k) for h in ring_hexs if h != business_h3])
        
        if not available_positions:
            logger.warning("⚠️ No se encontraron posiciones para riders")
            return []
        
        # Seleccionar posiciones para riders
        selected_positions = random.sample(
            available_positions, 
            min(count, len(available_positions))
        )
        
        riders = []
        for i, (h3_pos, distance_k) in enumerate(selected_positions):
            lat, lon = self.h3_engine.h3_to_latlng(h3_pos)
            
            if lat and lon:
                rider = {
                    'id': i + 1,
                    'nombre': f'Rider-{chr(65+i)}',  # A, B, C, D
                    'h3_position': h3_pos,
                    'lat': lat,
                    'lon': lon,
                    'distance_from_business_hexs': distance_k,
                    'distance_from_business_m': distance_k * self.h3_engine.approx_hex_radius_m,
                    'status': 'disponible'
                }
                riders.append(rider)
        
        # Seleccionar 1 rider más cercano al negocio
        if riders:
            closest_rider = min(riders, key=lambda r: r['distance_from_business_hexs'])
            closest_rider['selected'] = True
            closest_rider['status'] = 'asignado'
            
            logger.info(f"🛵 {len(riders)} riders creados, {closest_rider['nombre']} seleccionado")
        
        return riders
    
    def get_selected_rider(self, riders: List[Dict]) -> Optional[Dict]:
        """Obtener el rider seleccionado"""
        for rider in riders:
            if rider.get('selected', False):
                return rider
        
        # Si no hay seleccionado, usar el primero
        if riders:
            riders[0]['selected'] = True
            riders[0]['status'] = 'asignado'
            return riders[0]
        
        return None


class RouteAnalyzer:
    """Analizador de rutas H3 para extracción OSM"""
    
    def __init__(self, h3_engine: H3SpatialEngine):
        self.h3_engine = h3_engine
    
    def analyze_delivery_routes(self, business_h3: str, client_h3: str, 
                              rider_h3: str) -> Dict:
        """Analizar todas las rutas de delivery y obtener H3s únicos"""
        
        # Ruta 1: Cliente → Negocio (para entender la zona)
        route_client_business = self.h3_engine.h3_line(client_h3, business_h3)
        
        # Ruta 2: Rider → Negocio (recoger pedido)  
        route_rider_business = self.h3_engine.h3_line(rider_h3, business_h3)
        
        # Ruta 3: Rider → Cliente (delivery final)
        route_rider_client = self.h3_engine.h3_line(rider_h3, client_h3)
        
        # Combinar todos los H3s únicos
        all_h3s = list(set(
            route_client_business + 
            route_rider_business + 
            route_rider_client
        ))
        
        # Calcular bounding box total
        bbox = self._calculate_bbox_from_h3s(all_h3s)
        
        result = {
            'route_client_business': route_client_business,
            'route_rider_business': route_rider_business,
            'route_rider_client': route_rider_client,
            'all_unique_h3s': all_h3s,
            'total_hexagons': len(all_h3s),
            'bbox': bbox,
            'analysis': {
                'client_business_hexs': len(route_client_business),
                'rider_business_hexs': len(route_rider_business),
                'rider_client_hexs': len(route_rider_client),
                'area_coverage_km2': self._estimate_area_km2(bbox) if bbox else 0
            }
        }
        
        logger.info(f"📍 Rutas analizadas: {len(all_h3s)} hexágonos únicos")
        
        return result
    
    def _calculate_bbox_from_h3s(self, h3_list: List[str]) -> Optional[Dict]:
        """Calcular bounding box de lista de H3s"""
        if not h3_list:
            return None
        
        lats, lons = [], []
        
        for h3_cell in h3_list:
            lat, lon = self.h3_engine.h3_to_latlng(h3_cell)
            if lat and lon:
                lats.append(lat)
                lons.append(lon)
        
        if not lats:
            return None
        
        # Buffer extra para asegurar cobertura completa
        buffer = 0.002  # ~200m
        
        return {
            'south': min(lats) - buffer,
            'north': max(lats) + buffer,
            'west': min(lons) - buffer,
            'east': max(lons) + buffer
        }
    
    def _estimate_area_km2(self, bbox: Dict) -> float:
        """Estimar área cubierta en km²"""
        if not bbox:
            return 0.0
        
        lat_diff = bbox['north'] - bbox['south']
        lon_diff = bbox['east'] - bbox['west']
        
        # Conversión aproximada a km²
        return abs(lat_diff * lon_diff) * (111 ** 2)


# Instancias globales para usar en tasks
h3_engine = H3SpatialEngine(resolution=9)  # ~174m radius
rider_manager = RiderManager(h3_engine)
route_analyzer = RouteAnalyzer(h3_engine)
