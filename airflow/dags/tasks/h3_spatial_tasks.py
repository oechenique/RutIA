"""
🔶 RutIA H3 Spatial Tasks
Análisis hexagonal H3 + creación de riders + trazado de rutas espaciales + BUFFER GUSANAL
"""

import random
import math
from typing import Dict, List
from shapely.geometry import Point, LineString
from utils.h3_utils import h3_engine, rider_manager, route_analyzer
from utils.logging_utils import webinar_logger, metrics_collector

def task_analisis_h3_termonuclear(**context):
    """🎬 H3 ANALYSIS: Sistema hexagonal + riders inteligentes"""
    
    ti = context['task_instance']
    coords_data = ti.xcom_pull(task_ids='geocoding_termonuclear')
    
    empresa = coords_data['empresa']
    cliente = coords_data['cliente']
    
    webinar_logger.log_step_start(
        "ANÁLISIS H3 TERMONUCLEAR",
        {
            "empresa_coords": [empresa['lat'], empresa['lon']], 
            "cliente_coords": [cliente['lat'], cliente['lon']],
            "h3_resolution": h3_engine.resolution
        }
    )
    
    # Convertir coordenadas a H3 hexágonos
    empresa_h3 = h3_engine.latlng_to_h3(empresa['lat'], empresa['lon'])
    cliente_h3 = h3_engine.latlng_to_h3(cliente['lat'], cliente['lon'])
    
    if not empresa_h3 or not cliente_h3:
        error_msg = "Error convirtiendo coordenadas a H3"
        webinar_logger.log_step_error("H3_CONVERSION", Exception(error_msg))
        raise Exception(error_msg)
    
    webinar_logger.log_spatial_analysis(
        "H3 HEXAGONAL CONVERSION",
        {
            "empresa_coords": [empresa['lat'], empresa['lon']],
            "cliente_coords": [cliente['lat'], cliente['lon']]
        },
        {
            "empresa_h3": empresa_h3,
            "cliente_h3": cliente_h3,
            "resolution": h3_engine.resolution,
            "hex_radius_m": h3_engine.approx_hex_radius_m
        },
        f"Cada ubicación convertida a hexágono H3 de ~{h3_engine.approx_hex_radius_m}m"
    )
    
    # Crear riders en hexágonos cercanos al negocio (2-4 hexágonos de distancia)
    riders = rider_manager.create_riders_around_business(
        empresa['lat'], empresa['lon'], 
        count=random.randint(3, 5)  # 3-5 riders
    )
    
    if not riders:
        error_msg = "No se pudieron crear riders"
        webinar_logger.log_step_error("RIDER_CREATION", Exception(error_msg))
        raise Exception(error_msg)
    
    # Seleccionar rider más cercano al negocio
    selected_rider = rider_manager.get_selected_rider(riders)
    
    webinar_logger.log_webinar_epic(
        "RIDERS CREADOS EN SISTEMA H3",
        f"{len(riders)} riders posicionados estratégicamente usando hexágonos H3",
        {
            "total_riders": len(riders),
            "selected_rider": {
                "nombre": selected_rider['nombre'],
                "h3_position": selected_rider['h3_position'],
                "distance_from_business": f"{selected_rider['distance_from_business_hexs']} hexágonos (~{selected_rider['distance_from_business_m']:.0f}m)"
            },
            "all_riders": [
                {
                    "nombre": r['nombre'],
                    "distance_hexs": r['distance_from_business_hexs'],
                    "distance_m": f"{r['distance_from_business_m']:.0f}m"
                } for r in riders
            ]
        },
        f"Riders posicionados usando geometría hexagonal = misma tecnología que Uber",
        "SPATIAL_MAGIC"
    )
    
    # Métricas
    metrics_collector.add_technology_used("H3")
    metrics_collector.add_technology_used("Uber_H3_System")
    metrics_collector.set_spatial_metric("empresa_h3", empresa_h3)
    metrics_collector.set_spatial_metric("cliente_h3", cliente_h3)
    metrics_collector.set_spatial_metric("riders_creados", len(riders))
    
    resultado_h3 = {
        'empresa_h3': empresa_h3,
        'cliente_h3': cliente_h3,
        'selected_rider': selected_rider,
        'all_riders': riders,
        'resolution': h3_engine.resolution,
        'hex_radius_m': h3_engine.approx_hex_radius_m
    }
    
    webinar_logger.log_step_success(
        "H3 ANALYSIS COMPLETADO",
        resultado_h3,
        {
            "h3_conversion_exitoso": True,
            "riders_posicionados": len(riders),
            "sistema_hexagonal": "H3 Uber Technologies"
        }
    )
    
    return resultado_h3


def create_buffer_h3s_gusanal(start_lat: float, start_lon: float,
                             end_lat: float, end_lon: float,
                             buffer_meters: int = 1000) -> List[str]:
    """
    🐛 CREAR GUSANO ESPACIAL con H3s intersectantes
    Exactamente como en tu imagen: línea + buffer + H3s que lo toquen
    """
    
    # 1. Crear línea directa (rosa en tu imagen)
    line = LineString([(start_lon, start_lat), (end_lon, end_lat)])
    
    # 2. Crear buffer en grados (negro en tu imagen)  
    buffer_degrees = buffer_meters / 111000  # ~111km por grado
    buffer_polygon = line.buffer(buffer_degrees)
    
    # 3. Sampling de puntos para encontrar H3s intersectantes
    minx, miny, maxx, maxy = buffer_polygon.bounds
    h3_candidates = set()
    
    # Grid fino para capturar TODOS los H3s que toquen el buffer
    step = 0.001  # ~100m entre muestras
    lat = miny
    while lat <= maxy:
        lon = minx
        while lon <= maxx:
            point = Point(lon, lat)
            
            # Si el punto toca el buffer (como hexágonos verdes en tu imagen)
            if buffer_polygon.contains(point) or buffer_polygon.distance(point) < 0.0005:
                h3_cell = h3_engine.latlng_to_h3(lat, lon)
                if h3_cell:
                    h3_candidates.add(h3_cell)
            
            lon += step
        lat += step
    
    webinar_logger.logger.info(f"🐛 Gusano espacial: {len(h3_candidates)} H3s en buffer {buffer_meters}m")
    
    return list(h3_candidates)


def task_trazado_rutas_h3(**context):
    """🐛 ROUTING H3 MEJORADO: Buffer gusanal para cobertura REAL"""
    
    ti = context['task_instance']
    h3_data = ti.xcom_pull(task_ids='analisis_h3_termonuclear')
    coords_data = ti.xcom_pull(task_ids='geocoding_termonuclear')
    
    empresa = coords_data['empresa']
    cliente = coords_data['cliente']
    rider = h3_data['selected_rider']
    
    empresa_h3 = h3_data['empresa_h3']
    cliente_h3 = h3_data['cliente_h3']
    rider_h3 = rider['h3_position']
    rider_nombre = rider['nombre']
    
    webinar_logger.log_step_start(
        "TRAZADO RUTAS H3 CON GUSANO ESPACIAL",
        {
            "empresa_coords": [empresa['lat'], empresa['lon']],
            "cliente_coords": [cliente['lat'], cliente['lon']],
            "rider_coords": [rider['lat'], rider['lon']],
            "buffer_method": "gusano_espacial_1000m"
        }
    )
    
    # MÉTODO ORIGINAL (para comparación)
    route_analysis_original = route_analyzer.analyze_delivery_routes(
        empresa_h3, cliente_h3, rider_h3
    )
    
    original_h3s = route_analysis_original['all_unique_h3s']
    original_count = len(original_h3s)
    
    # 🐛 NUEVO: GUSANO ESPACIAL empresa → cliente (como tu imagen)
    buffer_h3s_empresa_cliente = create_buffer_h3s_gusanal(
        empresa['lat'], empresa['lon'],
        cliente['lat'], cliente['lon'],
        buffer_meters=1000  # Buffer cómodo como pediste
    )
    
    # 🐛 NUEVO: GUSANO rider → empresa (buffer menor)
    buffer_h3s_rider_empresa = create_buffer_h3s_gusanal(
        rider['lat'], rider['lon'],
        empresa['lat'], empresa['lon'],
        buffer_meters=800  # Buffer menor para pickup
    )
    
    # COMBINAR: H3s originales + Gusanos espaciales
    all_unique_h3s = list(set(
        original_h3s +  # Rutas H3 originales
        buffer_h3s_empresa_cliente +  # Gusano empresa→cliente
        buffer_h3s_rider_empresa  # Gusano rider→empresa
    ))
    
    improved_count = len(all_unique_h3s)
    improvement_factor = improved_count / max(1, original_count)
    
    # Calcular bbox expandido
    bbox = route_analyzer._calculate_bbox_from_h3s(all_unique_h3s)
    area_km2 = route_analyzer._estimate_area_km2(bbox) if bbox else 0
    
    webinar_logger.log_webinar_epic(
        "🐛 GUSANO ESPACIAL ACTIVADO",
        f"Cobertura mejorada {improvement_factor:.1f}x: {improved_count} hexágonos vs {original_count} originales",
        {
            "metodo_original": f"{original_count} hexágonos (líneas H3 directas)",
            "metodo_gusanal": f"{improved_count} hexágonos (buffer espacial)",
            "mejora_factor": f"{improvement_factor:.1f}x más cobertura",
            "buffer_empresa_cliente": len(buffer_h3s_empresa_cliente),
            "buffer_rider_empresa": len(buffer_h3s_rider_empresa),
            "buffer_radius_m": 1000,
            "calles_estimadas": improved_count * 20,
            "area_km2": area_km2
        },
        f"Gusano espacial 1000m → {improved_count - original_count} hexágonos EXTRA para routing Dijkstra REAL",
        "TERMONUCLEAR"
    )
    
    # Resultado mejorado manteniendo estructura original
    route_analysis_improved = {
        'route_client_business': route_analysis_original['route_client_business'],
        'route_rider_business': buffer_h3s_rider_empresa,  
        'route_rider_client': buffer_h3s_empresa_cliente,
        'all_unique_h3s': all_unique_h3s,
        'total_hexagons': improved_count,
        'bbox': bbox,
        'analysis': {
            'client_business_hexs': len(route_analysis_original['route_client_business']),
            'rider_business_hexs': len(buffer_h3s_rider_empresa),
            'rider_client_hexs': len(buffer_h3s_empresa_cliente),
            'area_coverage_km2': area_km2,
            'improvement_method': 'gusano_espacial_buffer',
            'improvement_factor': improvement_factor,
            'buffer_meters': 1200
        }
    }
    
    # Métricas
    metrics_collector.set_spatial_metric("hexagonos_totales", improved_count)
    metrics_collector.set_spatial_metric("hexagonos_originales", original_count)
    metrics_collector.set_spatial_metric("mejora_factor", improvement_factor)
    metrics_collector.set_spatial_metric("metodo_buffer", "gusano_espacial")
    metrics_collector.set_spatial_metric("area_cobertura_km2", area_km2)
    metrics_collector.set_spatial_metric("bbox_calculado", bbox)
    
    # Preparar resultado completo (manteniendo API original)
    rutas_resultado = {
        'route_analysis': route_analysis_improved,
        'rider_info': {
            'nombre': rider_nombre,
            'h3_position': rider_h3
        },
        'spatial_coverage': {
            'total_hexagons': improved_count,
            'original_hexagons': original_count,
            'improvement_factor': improvement_factor,
            'area_km2': area_km2,
            'bbox': bbox,
            'method': 'gusano_espacial_enhanced'
        }
    }
    
    webinar_logger.log_step_success(
        "TRAZADO RUTAS GUSANAL COMPLETADO",
        {
            "hexagonos_finales": improved_count,
            "mejora_aplicada": f"{improvement_factor:.1f}x",
            "metodo": "gusano_espacial_1000m",
            "routing_readiness": "OPTIMAL"
        },
        {
            "rutas_h3_calculadas": True,
            "hexagonos_para_osm": improved_count,
            "area_analisis_km2": area_km2,
            "buffer_method": "gusano_espacial"
        }
    )
    
    return rutas_resultado


def task_preparacion_extraccion_osm(**context):
    """🎬 PREP OSM: Preparar parámetros para extracción OSM masiva"""
    
    ti = context['task_instance']
    rutas_data = ti.xcom_pull(task_ids='trazado_rutas_h3')
    
    route_analysis = rutas_data['route_analysis']
    all_h3s = route_analysis['all_unique_h3s']
    bbox = route_analysis['bbox']
    
    webinar_logger.log_step_start(
        "PREPARACIÓN EXTRACCIÓN OSM",
        {
            "hexagonos_a_procesar": len(all_h3s),
            "bbox": bbox
        }
    )
    
    # Validar bbox
    if not bbox:
        error_msg = "Bounding box no calculado correctamente"
        webinar_logger.log_step_error("BBOX_VALIDATION", Exception(error_msg))
        raise Exception(error_msg)
    
    # Calcular estadísticas de la extracción
    area_km2 = abs((bbox['east'] - bbox['west']) * (bbox['north'] - bbox['south'])) * (111 ** 2)
    
    # Estimar cantidad de calles esperadas (aproximación)
    estimated_ways = estimate_osm_ways_in_area(area_km2, len(all_h3s))
    
    # Preparar parámetros para Overpass API
    overpass_params = {
        'bbox': bbox,
        'hexagons': all_h3s,
        'area_km2': area_km2,
        'estimated_ways': estimated_ways,
        'highway_types': ['primary', 'secondary', 'tertiary', 'residential', 'trunk', 'unclassified', 'living_street']
    }
    
    webinar_logger.log_webinar_epic(
        "PARÁMETROS OSM CALCULADOS",
        f"Preparación para extraer calles de {len(all_h3s)} hexágonos en {area_km2:.2f} km²",
        {
            "hexagonos_objetivo": len(all_h3s),
            "area_extraccion_km2": area_km2,
            "calles_estimadas": estimated_ways,
            "tipos_vias": overpass_params['highway_types'],
            "bbox_coordinates": bbox
        },
        f"UN pedido simple va a extraer ~{estimated_ways} calles de OpenStreetMap",
        "MIND_BLOWING"
    )
    
    # Métricas
    metrics_collector.set_spatial_metric("area_osm_km2", area_km2)
    metrics_collector.set_spatial_metric("calles_estimadas", estimated_ways)
    
    webinar_logger.log_step_success(
        "PREPARACIÓN OSM COMPLETADA",
        overpass_params,
        {
            "parametros_calculados": True,
            "area_objetivo_km2": area_km2,
            "extraccion_lista": True
        }
    )
    
    return overpass_params


def estimate_osm_ways_in_area(area_km2: float, hexagon_count: int) -> int:
    """Estimar cantidad de ways OSM en el área"""
    
    # Densidades aproximadas por tipo de zona (ways por km²)
    density_estimates = {
        'urban_high': 200,    # Zona urbana densa
        'urban_medium': 120,  # Zona urbana media
        'residential': 80,    # Zona residencial
        'suburban': 40        # Zona suburbana
    }
    
    # Usar densidad media-alta para CABA/Buenos Aires
    base_density = density_estimates['urban_medium']
    
    # Ajustar por cantidad de hexágonos (más hexágonos = más densidad esperada)
    density_factor = min(1.5, 1 + (hexagon_count / 50))
    
    estimated_ways = int(area_km2 * base_density * density_factor)
    
    # Asegurar mínimo razonable
    return max(estimated_ways, 30)


def validate_h3_route_quality(route_analysis: Dict) -> Dict:
    """Validar calidad de las rutas H3 generadas"""
    
    quality_score = 0.0
    issues = []
    
    # Validar que las rutas tienen hexágonos
    if route_analysis['total_hexagons'] > 0:
        quality_score += 0.4
    else:
        issues.append("No se generaron hexágonos en las rutas")
    
    # Validar bbox
    if route_analysis['bbox']:
        quality_score += 0.3
    else:
        issues.append("Bounding box no calculado")
    
    # Validar cobertura de área razonable
    area_km2 = route_analysis['analysis'].get('area_coverage_km2', 0)
    if 0.1 <= area_km2 <= 50:  # Entre 0.1 y 50 km² es razonable
        quality_score += 0.3
    else:
        issues.append(f"Área de cobertura inusual: {area_km2:.2f} km²")
    
    return {
        'quality_score': quality_score,
        'is_valid': quality_score >= 0.7,
        'issues': issues,
        'recommendations': generate_quality_recommendations(quality_score, issues)
    }


def generate_quality_recommendations(quality_score: float, issues: List[str]) -> List[str]:
    """Generar recomendaciones basadas en calidad de rutas"""
    
    recommendations = []
    
    if quality_score < 0.5:
        recommendations.append("Revisar coordenadas de entrada - pueden estar fuera de rango")
        recommendations.append("Verificar configuración H3 - resolución puede ser incorrecta")
    
    if 'No se generaron hexágonos' in str(issues):
        recommendations.append("Verificar que las coordenadas sean válidas para H3")
        recommendations.append("Revisar compatibilidad de librería H3")
    
    if 'Bounding box' in str(issues):
        recommendations.append("Verificar cálculo de boundaries H3")
        recommendations.append("Asegurar que los hexágonos tengan coordenadas válidas")
    
    if not recommendations:
        recommendations.append("Rutas H3 generadas correctamente - listo para extracción OSM")
    
    return recommendations