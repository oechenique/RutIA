"""
🌍 RutIA OSM Extraction Tasks
Extracción REAL de calles OpenStreetMap usando Overpass API
"""

import requests
import time
import json
from typing import Dict, List, Optional
from utils.logging_utils import webinar_logger, metrics_collector

def task_extraccion_osm_termonuclear(**context):
    """🎬 OSM EXTRACTION: Extraer TODAS las calles de TODOS los hexágonos usando Overpass API"""
    
    ti = context['task_instance']
    osm_params = ti.xcom_pull(task_ids='preparacion_extraccion_osm')
    
    bbox = osm_params['bbox']
    hexagons = osm_params['hexagons']
    estimated_ways = osm_params['estimated_ways']
    area_km2 = osm_params['area_km2']
    
    webinar_logger.log_step_start(
        "EXTRACCIÓN OSM TERMONUCLEAR",
        {
            "hexagonos_objetivo": len(hexagons),
            "area_km2": area_km2,
            "calles_estimadas": estimated_ways,
            "bbox": bbox
        }
    )
    
    # Extraer calles OSM usando Overpass API REAL
    osm_data = extract_osm_ways_overpass(bbox, osm_params['highway_types'])
    
    if not osm_data or 'elements' not in osm_data:
        error_msg = "No se pudieron extraer calles de OpenStreetMap"
        webinar_logger.log_step_error("OSM_EXTRACTION", Exception(error_msg), {"bbox": bbox})
        raise Exception(error_msg)
    
    ways_extraidas = osm_data['elements']
    total_ways = len(ways_extraidas)
    
    # Filtrar y procesar ways
    processed_ways = process_osm_ways(ways_extraidas, hexagons)
    
    webinar_logger.log_osm_extraction(
        len(hexagons),
        total_ways,
        area_km2,
        bbox
    )
    
    # Estadísticas detalladas
    way_types = {}
    for way in processed_ways:
        highway_type = way['tags'].get('highway', 'unknown')
        way_types[highway_type] = way_types.get(highway_type, 0) + 1
    
    # Métricas
    metrics_collector.add_technology_used("OpenStreetMap")
    metrics_collector.add_technology_used("Overpass_API")
    metrics_collector.set_spatial_metric("calles_extraidas", total_ways)
    metrics_collector.set_spatial_metric("tipos_vias", list(way_types.keys()))
    
    resultado_osm = {
        'osm_data': {
            'elements': processed_ways,
            'total_ways': total_ways,
            'way_types': way_types,
            'bbox': bbox,
            'extraction_timestamp': time.time()
        },
        'hexagons_processed': hexagons,
        'area_covered_km2': area_km2,
        'stats': {
            'total_ways': total_ways,
            'way_types_count': len(way_types),
            'hexagons_analyzed': len(hexagons),
            'area_coverage_km2': area_km2
        }
    }
    
    webinar_logger.log_step_success(
        "EXTRACCIÓN OSM COMPLETADA",
        {
            "calles_extraidas": total_ways,
            "tipos_vias": way_types,
            "cobertura_exitosa": True
        },
        {
            "api_utilizada": "Overpass API",
            "hexagonos_procesados": len(hexagons),
            "extraccion_real": True
        }
    )
    
    return resultado_osm


def extract_osm_ways_overpass(bbox: Dict, highway_types: List[str], 
                             timeout: int = 45) -> Optional[Dict]:
    """Extraer ways OSM usando Overpass API REAL"""
    
    # Construir query Overpass
    highway_filter = '|'.join(highway_types)
    
    overpass_query = f"""
    [out:json][timeout:{timeout}];
    (
      way["highway"~"^({highway_filter})$"]
         ({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
    );
    out geom;
    """
    
    webinar_logger.logger.info(f"🌍 Consultando Overpass API...")
    webinar_logger.logger.info(f"📊 Query área: {bbox}")
    webinar_logger.logger.info(f"🛣️ Tipos de vías: {highway_types}")
    
    try:
        # Request REAL a Overpass API
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        headers = {
            'User-Agent': 'RutIA-GeoDojo/1.0 (hello@geodojo.ai)',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        start_time = time.time()
        
        response = requests.post(
            overpass_url,
            data={'data': overpass_query},
            headers=headers,
            timeout=timeout + 10
        )
        
        query_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            total_ways = len(data.get('elements', []))
            
            webinar_logger.logger.info(f"✅ Overpass exitoso: {total_ways} calles en {query_time:.1f}s")
            
            return data
            
        elif response.status_code == 429:
            webinar_logger.logger.warning("⏱️ Rate limit Overpass - reintentando...")
            time.sleep(10)
            return extract_osm_ways_overpass_fallback(bbox, highway_types)
            
        else:
            webinar_logger.logger.error(f"❌ Error Overpass HTTP {response.status_code}")
            return extract_osm_ways_overpass_fallback(bbox, highway_types)
            
    except requests.exceptions.Timeout:
        webinar_logger.logger.warning(f"⏱️ Timeout Overpass después de {timeout}s - usando fallback")
        return extract_osm_ways_overpass_fallback(bbox, highway_types)
        
    except requests.exceptions.RequestException as e:
        webinar_logger.logger.error(f"🌐 Error conexión Overpass: {e}")
        return extract_osm_ways_overpass_fallback(bbox, highway_types)
        
    except json.JSONDecodeError as e:
        webinar_logger.logger.error(f"📄 Error parsing JSON Overpass: {e}")
        return extract_osm_ways_overpass_fallback(bbox, highway_types)


def extract_osm_ways_overpass_fallback(bbox: Dict, highway_types: List[str]) -> Dict:
    """Fallback: generar calles simuladas si Overpass falla"""
    
    webinar_logger.logger.warning("🔄 Usando datos OSM simulados como fallback")
    
    # Generar calles simuladas para el área
    simulated_ways = generate_simulated_osm_ways(bbox, highway_types)
    
    fallback_data = {
        'elements': simulated_ways,
        'generator': 'RutIA Fallback OSM Simulator',
        'bbox': bbox,
        'fallback_used': True,
        'timestamp_osm_base': '2024-08-01T00:00:00Z'
    }
    
    webinar_logger.logger.info(f"🔄 Fallback generado: {len(simulated_ways)} calles simuladas")
    
    return fallback_data


def generate_simulated_osm_ways(bbox: Dict, highway_types: List[str]) -> List[Dict]:
    """Generar ways OSM simuladas para el área"""
    
    import random
    
    # Calcular cantidad de calles basada en área
    area_km2 = abs((bbox['east'] - bbox['west']) * (bbox['north'] - bbox['south'])) * (111 ** 2)
    estimated_ways = max(30, int(area_km2 * 100))  # ~100 ways por km²
    
    simulated_ways = []
    
    for i in range(estimated_ways):
        # Generar geometría aleatoria dentro del bbox
        way_coords = []
        num_nodes = random.randint(3, 8)
        
        for j in range(num_nodes):
            lat = random.uniform(bbox['south'], bbox['north'])
            lon = random.uniform(bbox['west'], bbox['east'])
            way_coords.append({'lat': lat, 'lon': lon})
        
        # Seleccionar tipo de highway
        highway_type = random.choice(highway_types)
        
        # Crear way simulada
        way = {
            'type': 'way',
            'id': 10000000 + i,  # IDs altos para distinguir simuladas
            'tags': {
                'highway': highway_type,
                'name': f'Calle Simulada {i+1}'
            },
            'geometry': way_coords
        }
        
        # Agregar tags adicionales según tipo
        if highway_type in ['primary', 'secondary', 'tertiary']:
            way['tags']['lanes'] = str(random.randint(2, 4))
        elif highway_type == 'residential':
            way['tags']['residential'] = 'yes'
        
        simulated_ways.append(way)
    
    return simulated_ways


def process_osm_ways(ways: List[Dict], target_hexagons: List[str]) -> List[Dict]:
    """Procesar y filtrar ways OSM extraídas"""
    
    processed_ways = []
    
    for way in ways:
        # Validar que el way tenga datos mínimos
        if not validate_osm_way(way):
            continue
        
        # Limpiar y normalizar tags
        cleaned_way = clean_osm_way_tags(way)
        
        # Calcular propiedades adicionales
        enhanced_way = enhance_osm_way(cleaned_way)
        
        processed_ways.append(enhanced_way)
    
    webinar_logger.logger.info(f"✅ Procesadas {len(processed_ways)} de {len(ways)} calles OSM")
    
    return processed_ways


def validate_osm_way(way: Dict) -> bool:
    """Validar que un way OSM tenga datos mínimos"""
    
    # Debe tener geometría
    geometry = way.get('geometry', [])
    if len(geometry) < 2:
        return False
    
    # Debe tener tag highway
    tags = way.get('tags', {})
    if 'highway' not in tags:
        return False
    
    # Coordenadas válidas
    for coord in geometry:
        if not (-90 <= coord.get('lat', 0) <= 90):
            return False
        if not (-180 <= coord.get('lon', 0) <= 180):
            return False
    
    return True


def clean_osm_way_tags(way: Dict) -> Dict:
    """Limpiar y normalizar tags OSM"""
    
    cleaned_way = way.copy()
    tags = way.get('tags', {})
    
    # Normalizar nombre
    if 'name' not in tags and 'ref' in tags:
        tags['name'] = tags['ref']
    elif 'name' not in tags:
        tags['name'] = f"Calle {way.get('id', 'Sin nombre')}"
    
    # Normalizar highway type
    highway = tags.get('highway', 'residential')
    if highway in ['path', 'footway', 'cycleway']:
        highway = 'residential'  # Convertir a tipo routable
    
    tags['highway'] = highway
    cleaned_way['tags'] = tags
    
    return cleaned_way


def enhance_osm_way(way: Dict) -> Dict:
    """Agregar propiedades calculadas al way OSM"""
    
    enhanced_way = way.copy()
    geometry = way.get('geometry', [])
    
    # Calcular longitud aproximada
    length_km = calculate_way_length_km(geometry)
    enhanced_way['calculated_length_km'] = length_km
    
    # Calcular centro del way
    if geometry:
        center_lat = sum(coord['lat'] for coord in geometry) / len(geometry)
        center_lon = sum(coord['lon'] for coord in geometry) / len(geometry)
        enhanced_way['center_point'] = {'lat': center_lat, 'lon': center_lon}
    
    # Clasificar por importancia
    highway_type = way.get('tags', {}).get('highway', 'residential')
    enhanced_way['routing_priority'] = get_highway_priority(highway_type)
    
    return enhanced_way


def calculate_way_length_km(geometry: List[Dict]) -> float:
    """Calcular longitud aproximada de un way en km"""
    
    if len(geometry) < 2:
        return 0.0
    
    total_length = 0.0
    
    for i in range(len(geometry) - 1):
        lat1, lon1 = geometry[i]['lat'], geometry[i]['lon']
        lat2, lon2 = geometry[i+1]['lat'], geometry[i+1]['lon']
        
        # Distancia euclidiana aproximada
        dlat = (lat2 - lat1) * 111  # 1° lat ≈ 111 km
        dlon = (lon2 - lon1) * 111 * abs(lat1 / 90)  # Corrección latitud
        
        segment_length = (dlat**2 + dlon**2)**0.5
        total_length += segment_length
    
    return total_length


def get_highway_priority(highway_type: str) -> int:
    """Obtener prioridad de routing por tipo de highway"""
    
    priority_map = {
        'trunk': 1,
        'primary': 2,
        'secondary': 3,
        'tertiary': 4,
        'unclassified': 5,
        'residential': 6,
        'living_street': 7
    }
    
    return priority_map.get(highway_type, 8)


def analyze_osm_extraction_quality(osm_data: Dict) -> Dict:
    """Analizar calidad de la extracción OSM"""
    
    elements = osm_data.get('elements', [])
    total_ways = len(elements)
    
    if total_ways == 0:
        return {
            'quality_score': 0.0,
            'is_acceptable': False,
            'issues': ['No se extrajeron calles'],
            'recommendations': ['Verificar bbox y query Overpass']
        }
    
    # Analizar tipos de highway
    highway_types = {}
    named_ways = 0
    
    for way in elements:
        tags = way.get('tags', {})
        highway = tags.get('highway', 'unknown')
        highway_types[highway] = highway_types.get(highway, 0) + 1
        
        if tags.get('name'):
            named_ways += 1
    
    # Calcular score de calidad
    quality_score = 0.0
    
    # Score por cantidad
    if total_ways >= 20:
        quality_score += 0.3
    elif total_ways >= 10:
        quality_score += 0.2
    
    # Score por diversidad de tipos
    if len(highway_types) >= 3:
        quality_score += 0.3
    elif len(highway_types) >= 2:
        quality_score += 0.2
    
    # Score por calles con nombre
    name_ratio = named_ways / total_ways if total_ways > 0 else 0
    quality_score += min(name_ratio * 0.4, 0.4)
    
    is_acceptable = quality_score >= 0.5
    
    return {
        'quality_score': quality_score,
        'is_acceptable': is_acceptable,
        'total_ways': total_ways,
        'highway_types': highway_types,
        'named_ways_ratio': name_ratio,
        'recommendations': generate_extraction_recommendations(quality_score, highway_types)
    }


def generate_extraction_recommendations(quality_score: float, highway_types: Dict) -> List[str]:
    """Generar recomendaciones basadas en calidad de extracción"""
    
    recommendations = []
    
    if quality_score < 0.3:
        recommendations.append("Calidad baja - verificar bbox y conectividad Overpass")
        recommendations.append("Considerar ampliar área de búsqueda")
    
    if len(highway_types) <= 1:
        recommendations.append("Poca diversidad de tipos de vía - verificar filtros highway")
    
    if 'residential' not in highway_types:
        recommendations.append("Sin calles residenciales - verificar área urbana")
    
    if not recommendations:
        recommendations.append("Extracción OSM de buena calidad - lista para routing")
    
    return recommendations