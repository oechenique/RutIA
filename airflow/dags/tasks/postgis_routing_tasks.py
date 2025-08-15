"""
🛣️ RutIA pgRouting Tasks
Implementación REAL de pgRouting con algoritmo Dijkstra sobre calles OSM
"""

from typing import Dict, List, Optional, Tuple
from utils.db_utils import db_manager
from utils.logging_utils import webinar_logger, metrics_collector

def task_almacenamiento_postgis(**context):
    """🎬 POSTGIS STORAGE: Guardar red vial OSM en PostGIS para routing"""
    
    ti = context['task_instance']
    osm_data = ti.xcom_pull(task_ids='extraccion_osm_termonuclear')
    
    if 'error' in str(osm_data) or not osm_data.get('osm_data', {}).get('elements'):
        error_msg = "No hay datos OSM válidos para almacenar"
        webinar_logger.log_step_error("POSTGIS_STORAGE", Exception(error_msg))
        raise Exception(error_msg)
    
    ways_osm = osm_data['osm_data']['elements']
    area_km2 = osm_data['area_covered_km2']
    
    webinar_logger.log_step_start(
        "ALMACENAMIENTO POSTGIS",
        {
            "calles_a_guardar": len(ways_osm),
            "area_cubierta_km2": area_km2
        }
    )
    
    # Limpiar tabla y crear estructura si es necesario
    db_manager.create_osm_routing_table()
    db_manager.clear_routing_table()
    
    # Insertar ways OSM en PostGIS
    inserted_count = 0
    
    for i, way in enumerate(ways_osm):
        try:
            # Procesar way individual
            processed_ways = process_way_for_postgis(way, f"batch_{i//100}")
            
            # Insertar en base de datos
            count = db_manager.insert_osm_ways(processed_ways, f"osm_way_{way.get('id', i)}")
            inserted_count += count
            
        except Exception as e:
            webinar_logger.logger.error(f"❌ Error procesando way {way.get('id', i)}: {e}")
            continue
    
    if inserted_count == 0:
        error_msg = "No se pudieron insertar calles en PostGIS"
        webinar_logger.log_step_error("POSTGIS_INSERT", Exception(error_msg))
        raise Exception(error_msg)
    
    # Preparar topology para pgRouting
    topology_ready = db_manager.prepare_pgrouting_topology()
    
    if not topology_ready:
        webinar_logger.logger.warning("⚠️ Problemas preparando topology - continuando con datos disponibles")
    
    webinar_logger.log_webinar_epic(
        "RED VIAL ALMACENADA EN POSTGIS",
        f"Red vial completa guardada: {inserted_count} calles listas para routing Dijkstra",
        {
            "calles_insertadas": inserted_count,
            "area_cubierta_km2": area_km2,
            "topology_preparada": topology_ready,
            "motor_routing": "pgRouting + PostGIS"
        },
        "PostGIS ahora tiene una red vial completa para calcular rutas REALES",
        "SPATIAL_MAGIC"
    )
    
    # Métricas
    metrics_collector.add_technology_used("PostGIS")
    metrics_collector.add_technology_used("pgRouting")
    metrics_collector.set_spatial_metric("calles_en_postgis", inserted_count)
    
    resultado_storage = {
        'calles_insertadas': inserted_count,
        'topology_ready': topology_ready,
        'postgis_ready': True,
        'area_covered_km2': area_km2
    }
    
    webinar_logger.log_step_success(
        "ALMACENAMIENTO POSTGIS COMPLETADO",
        resultado_storage,
        {
            "red_vial_lista": True,
            "routing_preparado": topology_ready
        }
    )
    
    return resultado_storage


def task_routing_dijkstra_termonuclear(**context):
    """🎬 ROUTING REAL: pgRouting Dijkstra sobre calles OSM reales"""
    
    ti = context['task_instance']
    storage_data = ti.xcom_pull(task_ids='almacenamiento_postgis')
    coords_data = ti.xcom_pull(task_ids='geocoding_termonuclear')
    h3_data = ti.xcom_pull(task_ids='analisis_h3_termonuclear')
    
    if not storage_data.get('postgis_ready'):
        error_msg = "PostGIS no está listo para routing"
        webinar_logger.log_step_error("ROUTING_PREP", Exception(error_msg))
        raise Exception(error_msg)
    
    # Coordenadas REALES para routing
    empresa = coords_data['empresa']
    cliente = coords_data['cliente']
    rider = h3_data['selected_rider']
    
    webinar_logger.log_step_start(
        "ROUTING DIJKSTRA REAL",
        {
            "rider_coords": [rider['lat'], rider['lon']],
            "empresa_coords": [empresa['lat'], empresa['lon']],
            "cliente_coords": [cliente['lat'], cliente['lon']],
            "calles_disponibles": storage_data['calles_insertadas']
        }
    )
    
    # Encontrar nodos más cercanos para routing
    rider_node = db_manager.find_closest_node(rider['lat'], rider['lon'])
    empresa_node = db_manager.find_closest_node(empresa['lat'], empresa['lon'])
    cliente_node = db_manager.find_closest_node(cliente['lat'], cliente['lon'])
    
    if not all([rider_node, empresa_node, cliente_node]):
        webinar_logger.logger.warning("⚠️ No se encontraron todos los nodos - usando routing aproximado")
        return calculate_fallback_routing(rider, empresa, cliente)
    
    webinar_logger.logger.info(f"📍 Nodos encontrados - Rider: {rider_node}, Empresa: {empresa_node}, Cliente: {cliente_node}")
    
    # CALCULAR RUTA REAL: Rider → Empresa
    ruta_rider_empresa = db_manager.calculate_dijkstra_route(rider_node, empresa_node)
    
    # CALCULAR RUTA REAL: Empresa → Cliente  
    ruta_empresa_cliente = db_manager.calculate_dijkstra_route(empresa_node, cliente_node)
    
    if not ruta_rider_empresa or not ruta_empresa_cliente:
        webinar_logger.logger.warning("⚠️ pgRouting falló - usando routing aproximado")
        return calculate_fallback_routing(rider, empresa, cliente)
    
    # Procesar resultados reales
    ruta_1_procesada = process_dijkstra_route(ruta_rider_empresa, "Rider → Empresa")
    ruta_2_procesada = process_dijkstra_route(ruta_empresa_cliente, "Empresa → Cliente")
    
    # Resultado final con rutas REALES
    routing_real = {
        'ruta_rider_empresa': ruta_1_procesada,
        'ruta_empresa_cliente': ruta_2_procesada,
        'ruta_completa': {
            'distancia_total_km': ruta_1_procesada['distancia_km'] + ruta_2_procesada['distancia_km'],
            'tiempo_total_minutos': ruta_1_procesada['tiempo_minutos'] + ruta_2_procesada['tiempo_minutos'] + 3, # +3 min pickup
            'calles_totales': len(ruta_1_procesada['calles_utilizadas']) + len(ruta_2_procesada['calles_utilizadas']),
            'tipos_vias': list(set(ruta_1_procesada['tipos_vias'] + ruta_2_procesada['tipos_vias'])),
            'segmentos_totales': ruta_1_procesada['segmentos_count'] + ruta_2_procesada['segmentos_count']
        },
        'routing_engine': 'pgRouting Dijkstra sobre calles OSM reales',
        'precision': 'metro_por_metro_sobre_calles_reales',
        'calles_analizadas': storage_data['calles_insertadas'],
        'nodes_used': {
            'rider_node': rider_node,
            'empresa_node': empresa_node,
            'cliente_node': cliente_node
        }
    }
    
    webinar_logger.log_pgrouting_analysis(
        routing_real['ruta_completa'],
        "Dijkstra"
    )
    
    # Métricas
    metrics_collector.set_spatial_metric("distancia_total_km", routing_real['ruta_completa']['distancia_total_km'])
    metrics_collector.set_spatial_metric("tiempo_total_min", routing_real['ruta_completa']['tiempo_total_minutos'])
    metrics_collector.set_spatial_metric("routing_algorithm", "Dijkstra")
    
    webinar_logger.log_step_success(
        "ROUTING DIJKSTRA COMPLETADO",
        {
            "distancia_total": f"{routing_real['ruta_completa']['distancia_total_km']:.2f}km",
            "tiempo_total": f"{routing_real['ruta_completa']['tiempo_total_minutos']:.1f} min",
            "calles_reales": routing_real['ruta_completa']['calles_totales']
        },
        {
            "algoritmo_usado": "Dijkstra",
            "routing_real": True,
            "calles_analizadas": storage_data['calles_insertadas']
        }
    )
    
    return routing_real


def process_way_for_postgis(way: Dict, batch_id: str) -> List[Dict]:
    """Procesar way OSM para inserción en PostGIS"""
    
    # Validar datos mínimos
    if not way.get('geometry') or len(way['geometry']) < 2:
        return []
    
    tags = way.get('tags', {})
    highway_type = tags.get('highway', 'residential')
    
    # Crear registro para PostGIS
    postgis_way = {
        'id': way.get('id', 0),
        'tags': tags,
        'geometry': way['geometry'],
        'highway_type': highway_type,
        'batch_id': batch_id
    }
    
    return [postgis_way]


def process_dijkstra_route(route_data: List[Dict], route_name: str) -> Dict:
    """Procesar resultado de pgRouting Dijkstra"""
    
    if not route_data:
        return {
            'error': f'no_route_found_{route_name}',
            'distancia_km': 0,
            'tiempo_minutos': 0,
            'calles_utilizadas': [],
            'tipos_vias': [],
            'segmentos_count': 0
        }
    
    # Procesar segmentos de la ruta
    distancia_total = 0
    tiempo_total = 0
    calles_utilizadas = []
    tipos_vias = []
    geometrias = []
    
    for segment in route_data:
        if segment.get('edge'):  # Solo segmentos con edge válido
            longitud = float(segment.get('longitud_km', 0) or 0)
            costo = float(segment.get('cost', 0) or 0)
            nombre = segment.get('nombre', '')
            tipo_highway = segment.get('tipo_highway', '')
            geometria = segment.get('geometria', '')
            
            distancia_total += longitud
            tiempo_total += costo
            
            if nombre and nombre not in calles_utilizadas:
                calles_utilizadas.append(nombre)
            
            if tipo_highway and tipo_highway not in tipos_vias:
                tipos_vias.append(tipo_highway)
            
            if geometria:
                geometrias.append(geometria)
    
    return {
        'distancia_km': distancia_total,
        'tiempo_minutos': tiempo_total,
        'calles_utilizadas': calles_utilizadas,
        'tipos_vias': tipos_vias,
        'segmentos_count': len([s for s in route_data if s.get('edge')]),
        'geometrias': geometrias,
        'algoritmo': 'pgRouting Dijkstra REAL',
        'route_name': route_name
    }


def calculate_fallback_routing(rider: Dict, empresa: Dict, cliente: Dict) -> Dict:
    """Calcular routing aproximado si pgRouting falla"""
    
    webinar_logger.logger.warning("🔄 Usando routing aproximado como fallback")
    
    # Calcular distancias euclidianas aproximadas
    dist_rider_empresa = calculate_euclidean_distance(
        rider['lat'], rider['lon'],
        empresa['lat'], empresa['lon']
    )
    
    dist_empresa_cliente = calculate_euclidean_distance(
        empresa['lat'], empresa['lon'],
        cliente['lat'], cliente['lon']
    )
    
    # Estimar tiempos (velocidad promedio 25 km/h en ciudad)
    tiempo_rider_empresa = (dist_rider_empresa / 25) * 60  # minutos
    tiempo_empresa_cliente = (dist_empresa_cliente / 25) * 60  # minutos
    
    return {
        'ruta_rider_empresa': {
            'distancia_km': dist_rider_empresa,
            'tiempo_minutos': tiempo_rider_empresa,
            'calles_utilizadas': ['Ruta aproximada'],
            'tipos_vias': ['unknown'],
            'segmentos_count': 1,
            'algoritmo': 'Euclidiano aproximado'
        },
        'ruta_empresa_cliente': {
            'distancia_km': dist_empresa_cliente,
            'tiempo_minutos': tiempo_empresa_cliente,
            'calles_utilizadas': ['Ruta aproximada'],
            'tipos_vias': ['unknown'],
            'segmentos_count': 1,
            'algoritmo': 'Euclidiano aproximado'
        },
        'ruta_completa': {
            'distancia_total_km': dist_rider_empresa + dist_empresa_cliente,
            'tiempo_total_minutos': tiempo_rider_empresa + tiempo_empresa_cliente + 3,
            'calles_totales': 2,
            'tipos_vias': ['unknown'],
            'segmentos_totales': 2
        },
        'routing_engine': 'Fallback euclidiano',
        'precision': 'aproximado_por_fallo_pgrouting',
        'fallback_used': True
    }


def calculate_euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcular distancia euclidiana aproximada en km"""
    
    import math
    
    # Conversión aproximada a km
    dlat = (lat2 - lat1) * 111  # 1° lat ≈ 111 km
    dlon = (lon2 - lon1) * 111 * math.cos(math.radians(lat1))  # Corrección latitud
    
    distance_km = math.sqrt(dlat**2 + dlon**2)
    
    return distance_km


def validate_routing_result(routing_result: Dict) -> Dict:
    """Validar calidad del resultado de routing"""
    
    ruta_completa = routing_result.get('ruta_completa', {})
    
    quality_score = 0.0
    issues = []
    
    # Validar distancia razonable
    distancia = ruta_completa.get('distancia_total_km', 0)
    if 0.1 <= distancia <= 50:  # Entre 100m y 50km es razonable
        quality_score += 0.3
    else:
        issues.append(f"Distancia inusual: {distancia:.2f} km")
    
    # Validar tiempo razonable
    tiempo = ruta_completa.get('tiempo_total_minutos', 0)
    if 1 <= tiempo <= 120:  # Entre 1 min y 2 horas es razonable
        quality_score += 0.3
    else:
        issues.append(f"Tiempo inusual: {tiempo:.1f} minutos")
    
    # Validar que usó routing real
    if routing_result.get('routing_engine', '').startswith('pgRouting'):
        quality_score += 0.4
    elif routing_result.get('fallback_used'):
        quality_score += 0.2
        issues.append("Se usó routing aproximado")
    
    return {
        'quality_score': quality_score,
        'is_acceptable': quality_score >= 0.6,
        'issues': issues,
        'routing_type': 'real' if quality_score >= 0.7 else 'approximate',
        'recommendations': generate_routing_recommendations(quality_score, issues)
    }


def generate_routing_recommendations(quality_score: float, issues: List[str]) -> List[str]:
    """Generar recomendaciones para mejorar routing"""
    
    recommendations = []
    
    if quality_score < 0.5:
        recommendations.append("Calidad de routing baja - verificar red vial en PostGIS")
        recommendations.append("Revisar topology pgRouting")
    
    if 'Distancia inusual' in str(issues):
        recommendations.append("Verificar coordenadas de entrada")
        recommendations.append("Revisar cálculo de distancias")
    
    if 'routing aproximado' in str(issues):
        recommendations.append("Mejorar disponibilidad de pgRouting")
        recommendations.append("Verificar conexión a base de datos")
    
    if not recommendations:
        recommendations.append("Routing de buena calidad - listo para tracking")
    
    return recommendations


def optimize_routing_performance(routing_data: Dict) -> Dict:
    """Optimizar datos de routing para mejor performance"""
    
    optimized = routing_data.copy()
    
    # Simplificar geometrías si hay muchas
    for ruta_key in ['ruta_rider_empresa', 'ruta_empresa_cliente']:
        if ruta_key in optimized:
            geometrias = optimized[ruta_key].get('geometrias', [])
            if len(geometrias) > 50:  # Simplificar si hay muchas geometrías
                # Tomar cada N geometrías para reducir complejidad
                step = len(geometrias) // 30
                optimized[ruta_key]['geometrias'] = geometrias[::max(1, step)]
                optimized[ruta_key]['simplified'] = True
    
    # Redondear valores numéricos
    ruta_completa = optimized.get('ruta_completa', {})
    if 'distancia_total_km' in ruta_completa:
        ruta_completa['distancia_total_km'] = round(ruta_completa['distancia_total_km'], 2)
    if 'tiempo_total_minutos' in ruta_completa:
        ruta_completa['tiempo_total_minutos'] = round(ruta_completa['tiempo_total_minutos'], 1)
    
    return optimized


def create_route_summary(routing_data: Dict) -> Dict:
    """Crear resumen de ruta para mostrar al usuario"""
    
    ruta_completa = routing_data.get('ruta_completa', {})
    
    # Determinar tipo de zona basado en tipos de vías
    tipos_vias = ruta_completa.get('tipos_vias', [])
    zona_tipo = classify_route_area(tipos_vias)
    
    # Calcular velocidad promedio
    distancia = ruta_completa.get('distancia_total_km', 0)
    tiempo_horas = ruta_completa.get('tiempo_total_minutos', 0) / 60
    velocidad_promedio = distancia / tiempo_horas if tiempo_horas > 0 else 0
    
    summary = {
        'distancia_total': f"{distancia:.1f} km",
        'tiempo_estimado': f"{ruta_completa.get('tiempo_total_minutos', 0):.0f} min",
        'velocidad_promedio': f"{velocidad_promedio:.1f} km/h",
        'tipo_zona': zona_tipo,
        'calles_principales': get_main_streets(routing_data),
        'routing_quality': 'Real' if routing_data.get('routing_engine', '').startswith('pgRouting') else 'Aproximado',
        'precision': routing_data.get('precision', 'unknown')
    }
    
    return summary


def classify_route_area(tipos_vias: List[str]) -> str:
    """Clasificar tipo de zona basado en tipos de vías"""
    
    if not tipos_vias:
        return 'Desconocida'
    
    if 'trunk' in tipos_vias or 'primary' in tipos_vias:
        return 'Zona urbana principal'
    elif 'secondary' in tipos_vias or 'tertiary' in tipos_vias:
        return 'Zona urbana secundaria'  
    elif 'residential' in tipos_vias:
        return 'Zona residencial'
    else:
        return 'Zona mixta'


def get_main_streets(routing_data: Dict) -> List[str]:
    """Obtener las calles principales de la ruta"""
    
    all_streets = []
    
    # Recopilar calles de ambas rutas
    for ruta_key in ['ruta_rider_empresa', 'ruta_empresa_cliente']:
        ruta = routing_data.get(ruta_key, {})
        calles = ruta.get('calles_utilizadas', [])
        all_streets.extend(calles)
    
    # Filtrar y limitar
    unique_streets = list(set(all_streets))
    
    # Tomar máximo 5 calles principales
    main_streets = [street for street in unique_streets if street and street != 'Ruta aproximada'][:5]
    
    return main_streets


def generate_routing_geojson(routing_data: Dict) -> Dict:
    """Generar GeoJSON de la ruta para visualización"""
    
    features = []
    
    # Procesar cada ruta
    for ruta_key, color in [('ruta_rider_empresa', '#FF6B35'), ('ruta_empresa_cliente', '#004E89')]:
        ruta = routing_data.get(ruta_key, {})
        geometrias = ruta.get('geometrias', [])
        
        if geometrias:
            # Crear feature para esta ruta
            feature = {
                'type': 'Feature',
                'properties': {
                    'route_segment': ruta_key,
                    'distance_km': ruta.get('distancia_km', 0),
                    'time_minutes': ruta.get('tiempo_minutos', 0),
                    'color': color,
                    'algorithm': ruta.get('algoritmo', 'unknown')
                },
                'geometry': {
                    'type': 'MultiLineString',
                    'coordinates': []  # Se poblaría con las geometrías reales
                }
            }
            
            features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'properties': {
            'total_distance_km': routing_data.get('ruta_completa', {}).get('distancia_total_km', 0),
            'total_time_minutes': routing_data.get('ruta_completa', {}).get('tiempo_total_minutos', 0),
            'routing_engine': routing_data.get('routing_engine', 'unknown')
        }
    }
    
    return geojson
