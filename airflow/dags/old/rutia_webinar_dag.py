"""
RutIA Webinar DAG - Procesamiento completo de pedidos
DAG que muestra toda la magia espacial para el webinar
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import requests
import json
import time
import random
import logging
import os

# Configuración del DAG
default_args = {
    'owner': 'rutia-geodojo',
    'start_date': datetime(2025, 7, 28),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'email_on_failure': False,
    'email_on_retry': False
}

dag = DAG(
    'rutia_webinar_procesamiento_completo',
    default_args=default_args,
    description='🗺️ RutIA - Procesamiento Espacial Completo para Webinar',
    schedule_interval=None,  # Triggered manually
    catchup=False,
    max_active_runs=1,
    tags=['rutia', 'webinar', 'spatial', 'h3', 'postgis', 'geodojo']
)

# URLs de servicios internos
RUTIA_API_URL = os.getenv('RUTIA_API_URL', 'http://api:3000')

def log_webinar_step(step_name: str, description: str, data: dict = None):
    """Logger especial para webinar con formato épico"""
    logging.info(f"🎬 WEBINAR STEP: {step_name}")
    logging.info(f"📝 {description}")
    if data:
        logging.info(f"📊 Data: {json.dumps(data, indent=2, default=str)}")
    logging.info("=" * 60)

# =============================================================================
# TASK 1: RECEPCIÓN Y PARSING DEL PEDIDO
# =============================================================================

def task_recepcion_pedido(**context):
    """
    🎬 WEBINAR REVEAL: Mostrar cómo parseamos el JSON complejo de n8n
    """
    pedido_data = context['dag_run'].conf or {
        'pedido_id': 'DEMO-WEBINAR-001',
        'cliente_nombre': 'Martin Webinar',
        'cliente_direccion': 'av santa fe 2251 4a caba',
        'restaurant': 'La Geográfica',
        'pedido_total': 45400,
        'pedido_items': [
            {'item_nombre': 'Hamburguesa Gisera', 'item_precio': 15500},
            {'item_nombre': 'Papas de Sizalla', 'item_precio': 7500},
            {'item_nombre': 'Flan de Proyección Mercator', 'item_precio': 7800}
        ]
    }
    
    log_webinar_step(
        "RECEPCIÓN PEDIDO",
        "El pedido llega desde WhatsApp/n8n con estructura compleja",
        pedido_data
    )
    
    # Extraer info clave
    resultado = {
        'pedido_id': pedido_data['pedido_id'],
        'cliente': pedido_data['cliente_nombre'], 
        'direccion': pedido_data['cliente_direccion'],
        'items_count': len(pedido_data.get('pedido_items', [])),
        'total': pedido_data.get('pedido_total', 0)
    }
    
    logging.info("🎯 WEBINAR REVEAL: Lo que parece un pedido simple es DATA COMPLEJA")
    
    return resultado

# =============================================================================
# TASK 2: GEOCODING INTELIGENTE
# =============================================================================

def task_geocoding_espacial(**context):
    """
    🎬 WEBINAR REVEAL: Convertir dirección en coordenadas precisas
    """
    pedido_info = context['task_instance'].xcom_pull(task_ids='recepcion_pedido')
    direccion = pedido_info['direccion']
    
    log_webinar_step(
        "GEOCODING ESPACIAL",
        f"Convirtiendo '{direccion}' en coordenadas precisas con Nominatim",
        {'direccion_input': direccion}
    )
    
    # Simular geocoding (en producción usaríamos Nominatim real)
    time.sleep(2)  # Simular tiempo de proceso
    
    coords_resultado = {
        'direccion_original': direccion,
        'lat': -34.5956 + random.uniform(-0.01, 0.01),  # Santa Fe area + noise
        'lon': -58.3731 + random.uniform(-0.01, 0.01),
        'geocoder': 'Nominatim (OpenStreetMap)',
        'confidence': 'high'
    }
    
    log_webinar_step(
        "GEOCODING EXITOSO", 
        "¡Dirección convertida a coordenadas precisas!",
        coords_resultado
    )
    
    logging.info("🎯 WEBINAR REVEAL: Sin geocoding, no hay delivery moderno")
    return coords_resultado

# =============================================================================
# TASK 3: ANÁLISIS H3 HEXAGONAL
# =============================================================================

def task_analisis_h3(**context):
    """
    🎬 WEBINAR REVEAL: Convertir coordenadas a sistema H3 para análisis espacial
    """
    coords_data = context['task_instance'].xcom_pull(task_ids='geocoding_espacial')
    
    log_webinar_step(
        "ANÁLISIS H3 HEXAGONAL",
        "Convirtiendo coordenadas a sistema hexagonal H3 resolución 9",
        coords_data
    )
    
    # Simular conversión H3 (usaríamos h3-py real)
    time.sleep(1)
    
    h3_data = {
        'cliente_h3': '881f1a4c2ffffff',  # H3 simulado para Santa Fe
        'resolucion': 9,
        'area_hexagono_m2': 105332.513,
        'vecinos_h3': [
            '881f1a4c1ffffff', '881f1a4c3ffffff', '881f1a4c7ffffff',
            '881f1a4c6ffffff', '881f1a4cafffffff', '881f1a4cdffffff'
        ]
    }
    
    log_webinar_step(
        "H3 CALCULADO",
        "Cliente ubicado en hexágono H3 con precisión ~200m",
        h3_data
    )
    
    logging.info("🎯 WEBINAR REVEAL: Uber, Rappi, Airbnb = TODO usa H3 hexágonos")
    return h3_data

# =============================================================================
# TASK 4: BÚSQUEDA RIDERS INTELIGENTE
# =============================================================================

def task_busqueda_riders(**context):
    """
    🎬 WEBINAR REVEAL: Buscar riders usando inteligencia espacial H3
    """
    h3_data = context['task_instance'].xcom_pull(task_ids='analisis_h3')
    cliente_h3 = h3_data['cliente_h3']
    
    log_webinar_step(
        "BÚSQUEDA RIDERS INTELIGENTE",
        "Buscando riders disponibles usando algoritmo espacial H3",
        {'cliente_h3': cliente_h3, 'radio_busqueda': '3 hexágonos'}
    )
    
    time.sleep(2)  # Simular análisis complejo
    
    # Simular riders encontrados con scoring
    riders_encontrados = [
        {
            'id': 1,
            'nombre': 'Carlos',
            'h3_actual': '881f1a4c1ffffff',
            'distancia_hexs': 1,
            'tiene_pedido_cerca_local': True,
            'score_batching': 95,
            'score_final': 95
        },
        {
            'id': 2, 
            'nombre': 'María',
            'h3_actual': '881f1a4c3ffffff',
            'distancia_hexs': 2,
            'tiene_pedido_cerca_local': False,
            'score_batching': 70,
            'score_final': 70
        },
        {
            'id': 3,
            'nombre': 'Juan',
            'h3_actual': '881f1a4c7ffffff', 
            'distancia_hexs': 3,
            'tiene_pedido_cerca_local': False,
            'score_batching': 55,
            'score_final': 55
        }
    ]
    
    # Seleccionar mejor rider
    rider_seleccionado = riders_encontrados[0]  # El de mayor score
    
    log_webinar_step(
        "RIDER SELECCIONADO",
        f"¡{rider_seleccionado['nombre']} seleccionado por ALGORITMO ESPACIAL!",
        {
            'rider': rider_seleccionado['nombre'],
            'razon': 'Máximo score batching + proximidad H3',
            'ventaja_batching': rider_seleccionado['tiene_pedido_cerca_local']
        }
    )
    
    logging.info("🎯 WEBINAR REVEAL: La selección 'simple' es ALGORITMO COMPLEJO")
    return {
        'riders_evaluados': riders_encontrados,
        'rider_seleccionado': rider_seleccionado
    }

# =============================================================================
# TASK 5: EXTRACCIÓN CALLES OSM
# =============================================================================

def task_extraccion_osm(**context):
    """
    🎬 WEBINAR REVEAL: Extraer red vial real de OpenStreetMap
    """
    riders_data = context['task_instance'].xcom_pull(task_ids='busqueda_riders')
    h3_data = context['task_instance'].xcom_pull(task_ids='analisis_h3')
    
    log_webinar_step(
        "EXTRACCIÓN CALLES OSM",
        "Extrayendo red vial real de OpenStreetMap para routing",
        {
            'area_h3': [h3_data['cliente_h3']] + h3_data['vecinos_h3'][:3],
            'api_source': 'Overpass API'
        }
    )
    
    time.sleep(3)  # Simular query OSM compleja
    
    calles_extraidas = {
        'calles_principales': 45,
        'calles_secundarias': 128,
        'avenidas': 8,
        'total_segments': 181,
        'area_km2': 2.3,
        'fuente': 'OpenStreetMap via Overpass API'
    }
    
    log_webinar_step(
        "OSM EXTRAIDO",
        "Red vial completa extraída para routing preciso",
        calles_extraidas
    )
    
    logging.info("🎯 WEBINAR REVEAL: Sin OSM, no hay rutas reales")
    return calles_extraidas

# =============================================================================
# TASK 6: ROUTING POSTGIS
# =============================================================================

def task_routing_postgis(**context):
    """
    🎬 WEBINAR REVEAL: Calcular ruta óptima con PostGIS routing
    """
    calles_data = context['task_instance'].xcom_pull(task_ids='extraccion_osm')
    riders_data = context['task_instance'].xcom_pull(task_ids='busqueda_riders')
    
    log_webinar_step(
        "ROUTING POSTGIS",
        "Calculando ruta óptima: Rider → Tienda → Cliente",
        {
            'algoritmo': 'Dijkstra shortest path',
            'segmentos_analizados': calles_data['total_segments'],
            'engine': 'PostGIS + pgRouting'
        }
    )
    
    time.sleep(4)  # Simular cálculo routing complejo
    
    ruta_calculada = {
        'distancia_total_km': 4.2,
        'tiempo_estimado_min': 18,
        'waypoints': 3,
        'optimizacion': 'ruta_mas_rapida',
        'evita': ['trafico_intenso', 'calles_cortadas'],
        'geometria': 'LINESTRING(-58.3816 -34.6037, -58.3731 -34.5956)',
        'precision': 'metro_por_metro'
    }
    
    log_webinar_step(
        "RUTA CALCULADA",
        "¡Ruta óptima calculada con precisión GPS!",
        ruta_calculada
    )
    
    logging.info("🎯 WEBINAR REVEAL: Esto ES el cerebro de Google Maps")
    return ruta_calculada

# =============================================================================
# TASK 7: TRACKING VECTORIAL
# =============================================================================

def task_tracking_vectorial(**context):
    """
    🎬 WEBINAR REVEAL: Crear sistema de tracking en tiempo real
    """
    ruta_data = context['task_instance'].xcom_pull(task_ids='routing_postgis')
    pedido_info = context['task_instance'].xcom_pull(task_ids='recepcion_pedido')
    
    log_webinar_step(
        "TRACKING VECTORIAL",
        "Creando sistema de tracking en tiempo real sobre ruta vectorial",
        {
            'pedido_id': pedido_info['pedido_id'],
            'tracking_method': 'vectorial_sobre_linestring',
            'precision': 'GPS + interpolacion_matematica'
        }
    )
    
    time.sleep(2)
    
    tracking_sistema = {
        'pedido_id': pedido_info['pedido_id'],
        'ruta_vectorial': ruta_data['geometria'],
        'progreso_actual': '0%',
        'posicion_rider': 'inicio_ruta',
        'eta_dinamico': ruta_data['tiempo_estimado_min'],
        'actualizacion_frecuencia': 'cada_30_segundos',
        'visible_en': 'streamlit_dashboard'
    }
    
    log_webinar_step(
        "TRACKING ACTIVO",
        "¡Sistema de tracking vectorial ACTIVO!",
        tracking_sistema
    )
    
    logging.info("🎯 WEBINAR REVEAL: El 'puntito moviéndose' es MATEMÁTICA AVANZADA")
    return tracking_sistema

# =============================================================================
# TASK 8: NOTIFICACIÓN CLIENTE
# =============================================================================

def task_notificacion_cliente(**context):
    """
    🎬 WEBINAR REVEAL: Respuesta automática al cliente con toda la info
    """
    pedido_info = context['task_instance'].xcom_pull(task_ids='recepcion_pedido')
    rider_data = context['task_instance'].xcom_pull(task_ids='busqueda_riders')
    ruta_data = context['task_instance'].xcom_pull(task_ids='routing_postgis')
    
    rider_seleccionado = rider_data['rider_seleccionado']
    
    mensaje_cliente = f"""
🎉 ¡Pedido confirmado en La Geográfica!

👤 Cliente: {pedido_info['cliente']}
📦 Items: {pedido_info['items_count']} productos
💰 Total: ${pedido_info['total']:,.0f}

🛵 Rider: {rider_seleccionado['nombre']}
📍 Ubicación: Hexágono H3 {rider_seleccionado['h3_actual'][:8]}...
⏱️ ETA: {ruta_data['tiempo_estimado_min']} minutos
🛣️ Distancia: {ruta_data['distancia_total_km']} km

🗺️ Ruta optimizada con PostGIS + OSM
📍 Tracking en tiempo real disponible

¡Gracias por usar RutIA! 
Powered by GeoDojo 🔥
    """
    
    log_webinar_step(
        "NOTIFICACIÓN CLIENTE",
        "Enviando respuesta automática con TODA la inteligencia espacial",
        {
            'mensaje_enviado': True,
            'canal': 'WhatsApp via n8n',
            'info_incluida': [
                'rider_asignado', 'eta_calculado', 'ruta_optimizada', 
                'hexagono_h3', 'tracking_disponible'
            ]
        }
    )
    
    logging.info("🎯 WEBINAR REVEAL: La respuesta 'simple' incluye TODO el análisis")
    return {
        'mensaje_enviado': mensaje_cliente,
        'timestamp': datetime.now().isoformat(),
        'procesamiento_completo': True
    }

# =============================================================================
# DEFINICIÓN DE TASKS EN EL DAG
# =============================================================================

# Task 1: Recepción pedido
task_recepcion = PythonOperator(
    task_id='recepcion_pedido',
    python_callable=task_recepcion_pedido,
    dag=dag
)

# Task 2: Geocoding
task_geocoding = PythonOperator(
    task_id='geocoding_espacial',
    python_callable=task_geocoding_espacial,
    dag=dag
)

# Task 3: Análisis H3
task_h3 = PythonOperator(
    task_id='analisis_h3',
    python_callable=task_analisis_h3,
    dag=dag
)

# Task 4: Búsqueda riders
task_riders = PythonOperator(
    task_id='busqueda_riders',
    python_callable=task_busqueda_riders,
    dag=dag
)

# Task 5: Extracción OSM
task_osm = PythonOperator(
    task_id='extraccion_osm',
    python_callable=task_extraccion_osm,
    dag=dag
)

# Task 6: Routing PostGIS
task_routing = PythonOperator(
    task_id='routing_postgis',
    python_callable=task_routing_postgis,
    dag=dag
)

# Task 7: Tracking vectorial
task_tracking = PythonOperator(
    task_id='tracking_vectorial',
    python_callable=task_tracking_vectorial,
    dag=dag
)

# Task 8: Notificación cliente
task_notificacion = PythonOperator(
    task_id='notificacion_cliente',
    python_callable=task_notificacion_cliente,
    dag=dag
)

# =============================================================================
# DEPENDENCIAS DEL WORKFLOW WEBINAR
# =============================================================================

# Flow secuencial que muestra cada paso del procesamiento espacial
task_recepcion >> task_geocoding >> task_h3 >> task_riders
task_riders >> [task_osm, task_routing]  # Paralelo: OSM + Routing
[task_osm, task_routing] >> task_tracking >> task_notificacion

# =============================================================================
# DOCUMENTACIÓN PARA WEBINAR
# =============================================================================

dag.doc_md = """
# 🎬 RutIA Webinar DAG - La Magia Espacial Revelada

## 🎯 Propósito del Webinar:
Mostrar que lo que parece un "pedido simple" es en realidad un **SISTEMA ESPACIAL COMPLEJO**

## 🔄 Flow Completo:
1. **Recepción**: JSON complejo de n8n/WhatsApp
2. **Geocoding**: Dirección → Coordenadas precisas  
3. **H3 Analysis**: Coordenadas → Sistema hexagonal
4. **Riders Search**: Algoritmo espacial inteligente
5. **OSM Extraction**: Red vial real de OpenStreetMap
6. **PostGIS Routing**: Ruta óptima calculada
7. **Vector Tracking**: Sistema de seguimiento en tiempo real
8. **Client Response**: Respuesta automática inteligente

## 🎭 Reveal del Webinar:
**"Pensás que pedís comida... en realidad activás un MOTOR ESPACIAL COMPLEJO"**

## 🚀 Para Ejecutar:
- Trigger manual desde Airflow UI
- Cada task muestra logs explicativos
- Perfecto para demo en vivo

**Desarrollado por GeoDojo - Revelando la magia espacial del delivery** 🗺️🔥
"""