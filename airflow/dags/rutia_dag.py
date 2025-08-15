"""
🚀💥 RutIA DAG TERMONUCLEAR 💥🚀
Pipeline espacial completo que revela la magia detrás del delivery

Flow épico para el Webinar GeoDojo Septiembre 2025:
1. Recibe pedido real desde n8n 
2. Geocoding REAL con Nominatim
3. Análisis H3 + riders inteligentes
4. Trazado rutas hexagonales completas
5. Extracción OSM REAL con Overpass API
6. Almacenamiento en PostGIS
7. Routing Dijkstra REAL sobre calles OSM
8. Tracking vectorial en tiempo real
9. Notificaciones progresivas via n8n
10. Finalización con métricas épicas

¡LA REVELACIÓN DEL WEBINAR! 🎬
"Pensaste que pediste una hamburguesa... pero ejecutaste un SISTEMA ESPACIAL TERMONUCLEAR"
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Imports de nuestras tasks modulares
from tasks.geocoding_tasks import task_geocoding_termonuclear
from tasks.h3_spatial_tasks import (
    task_analisis_h3_termonuclear, 
    task_trazado_rutas_h3, 
    task_preparacion_extraccion_osm
)
from tasks.osm_extraction_tasks import task_extraccion_osm_termonuclear
from tasks.postgis_routing_tasks import (
    task_almacenamiento_postgis,
    task_routing_dijkstra_termonuclear
)
from tasks.notification_tasks import (
    task_tracking_vectorial,
    task_notificaciones_progresivas
)

# Utils para logging y métricas
from utils.logging_utils import webinar_logger, metrics_collector
from utils.db_utils import db_manager

import json
import time

# DAG Configuration
default_args = {
    'owner': 'rutia-geodojo-webinar',
    'start_date': datetime(2025, 8, 2),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'email_on_failure': False,
    'email_on_retry': False,
    'depends_on_past': False
}

dag = DAG(
    'rutia_termonuclear_procesamiento_espacial',
    default_args=default_args,
    description='🚀💥 RutIA Termonuclear - Pipeline Espacial Completo para Webinar GeoDojo',
    schedule_interval=None,  # Manual trigger desde n8n
    catchup=False,
    max_active_runs=1,
    tags=['rutia', 'termonuclear', 'spatial', 'h3', 'postgis', 'osm', 'webinar', 'geodojo']
)

# =============================================================================
# TASK 1: RECEPCIÓN Y ALMACENAMIENTO DEL PEDIDO
# =============================================================================

def task_recepcion_pedido_termonuclear(**context):
    """🎬 RECEPCIÓN: Del JSON REAL del cliente al análisis espacial complejo"""
    
    # Obtener data REAL del trigger (viene de la API que recibió de n8n)
    pedido_data = context['dag_run'].conf
    
    if not pedido_data:
        # Solo si NO viene nada (no debería pasar)
        pedido_data = {
            'pedido_id': 'NO-DATA-ERROR',
            'cliente_nombre': 'Sin datos del cliente',
            'cliente_direccion': 'Sin dirección especificada',
            'restaurant': 'La Geográfica',
            'pedido_total': 0,
            'pedido_items': []
        }
        webinar_logger.logger.error("❌ No se recibieron datos del pedido desde la API")
    else:
        # LOG ÉPICO con data REAL
        webinar_logger.log_webinar_epic(
            "PEDIDO REAL RECIBIDO DESDE n8n",
            f"Cliente REAL: {pedido_data.get('cliente_nombre', 'N/A')} en {pedido_data.get('cliente_direccion', 'N/A')}",
            {
                'cliente_real': pedido_data.get('cliente_nombre'),
                'direccion_real': pedido_data.get('cliente_direccion'), 
                'pedido_id_real': pedido_data.get('pedido_id'),
                'items_reales': [item.get('item_nombre', 'Item') for item in pedido_data.get('pedido_items', [])],
                'total_real': pedido_data.get('pedido_total', 0),
                'restaurant': pedido_data.get('restaurant', 'La Geográfica')
            },
            f"¡ESTO SÍ ES TERMONUCLEAR REAL! {pedido_data.get('cliente_nombre')} pidió {len(pedido_data.get('pedido_items', []))} items reales"
        )
    
    # Inicializar métricas del webinar con data REAL
    metrics_collector.add_step_completion("recepcion_pedido_real", 1.0, {
        'cliente_real': pedido_data.get('cliente_nombre', 'N/A'),
        'direccion_real': pedido_data.get('cliente_direccion', 'N/A'),
        'valor_real': pedido_data.get('pedido_total', 0)
    })
    
    # Guardar en PostgreSQL usando db_manager con data REAL
    try:
        pedido_db_id = db_manager.insert_pedido(pedido_data)
        
        webinar_logger.log_webinar_epic(
            "PEDIDO REAL ALMACENADO EN POSTGRESQL",
            f"Pedido REAL de {pedido_data.get('cliente_nombre', 'Cliente')} persistido con ID: {pedido_db_id}",
            {
                'pedido_db_id': pedido_db_id, 
                'status': 'procesando_espacial_real',
                'data_origen': 'n8n_via_api_real'
            },
            "Cada pedido REAL queda grabado para análisis espacial termonuclear completo"
        )
        
        return {
            'pedido_data': pedido_data,  # Data REAL del cliente
            'pedido_db_id': pedido_db_id,
            'status': 'received_and_stored_real',
            'processing_started_at': datetime.now().isoformat(),
            'data_source': 'real_client_via_n8n'
        }
        
    except Exception as e:
        webinar_logger.log_step_error("PEDIDO_STORAGE_REAL", e, pedido_data)
        raise

# =============================================================================
# TASK FINAL: MÉTRICAS Y FINALIZACIÓN ÉPICA
# =============================================================================

def task_finalizacion_termonuclear(**context):
    """🎬 FINALIZACIÓN: Métricas finales del procesamiento termonuclear"""
    
    ti = context['task_instance']
    
    # Recopilar datos de todas las tareas
    pedido_info = ti.xcom_pull(task_ids='recepcion_pedido_termonuclear')
    coords_data = ti.xcom_pull(task_ids='geocoding_termonuclear')
    h3_data = ti.xcom_pull(task_ids='analisis_h3_termonuclear')
    rutas_data = ti.xcom_pull(task_ids='trazado_rutas_h3')
    osm_data = ti.xcom_pull(task_ids='extraccion_osm_termonuclear')
    storage_data = ti.xcom_pull(task_ids='almacenamiento_postgis')
    routing_data = ti.xcom_pull(task_ids='routing_dijkstra_termonuclear')
    tracking_data = ti.xcom_pull(task_ids='tracking_vectorial')
    notification_data = ti.xcom_pull(task_ids='notificaciones_progresivas')
    
    # Compilar métricas finales para el webinar
    metricas_termonucleares = {
        'pedido_procesado': {
            'pedido_id': pedido_info['pedido_data']['pedido_id'],
            'cliente': pedido_info['pedido_data']['cliente_nombre'],
            'valor_total': pedido_info['pedido_data'].get('pedido_total', 0)
        },
        'procesamiento_espacial': {
            'geocoding_exitoso': True,
            'cliente_geocodificado': coords_data['cliente']['geocoder'],
            'h3_hexagonos_analizados': rutas_data['route_analysis']['total_hexagons'],
            'h3_resolution': h3_data['resolution'],
            'riders_evaluados': len(h3_data['all_riders']),
            'rider_seleccionado': h3_data['selected_rider']['nombre']
        },
        'extraccion_osm': {
            'calles_extraidas': osm_data['stats']['total_ways'],
            'area_analizada_km2': osm_data['area_covered_km2'],
            'api_utilizada': 'Overpass API',
            'tipos_vias_encontrados': len(osm_data['osm_data']['way_types'])
        },
        'routing_postgis': {
            'algoritmo': 'Dijkstra',
            'calles_en_postgis': storage_data['calles_insertadas'],
            'distancia_total_km': routing_data['ruta_completa']['distancia_total_km'],
            'tiempo_total_min': routing_data['ruta_completa']['tiempo_total_minutos'],
            'calles_utilizadas': routing_data['ruta_completa']['calles_totales'],
            'precision': 'metro_por_metro'
        },
        'tracking_sistema': {
            'estados_generados': len(tracking_data['tracking_states']),
            'update_frequency': '30_segundos',
            'precision': 'interpolacion_vectorial',
            'tracking_url_generada': notification_data['tracking_url']
        },
        'notificaciones': {
            'n8n_enviado': notification_data['notificacion_principal_enviada'],
            'cliente_notificado': True,
            'info_tecnica_incluida': notification_data['datos_tecnicos_incluidos']
        },
        'tecnologias_utilizadas': list(metrics_collector.metrics['technologies_used']),
        'webinar_metrics': metrics_collector.get_final_metrics(),
        'complejidad_nivel': 'TERMONUCLEAR 🚀💥'
    }
    
    # Logging épico final para webinar
    webinar_logger.log_final_metrics({
        'hexagonos_analizados': metricas_termonucleares['procesamiento_espacial']['h3_hexagonos_analizados'],
        'calles_extraidas': metricas_termonucleares['extraccion_osm']['calles_extraidas'],
        'area_km2': metricas_termonucleares['extraccion_osm']['area_analizada_km2'],
        'distancia_km': metricas_termonucleares['routing_postgis']['distancia_total_km'],
        'eta_minutos': int(metricas_termonucleares['routing_postgis']['tiempo_total_min']),
        'rider_nombre': metricas_termonucleares['procesamiento_espacial']['rider_seleccionado'],
        'tecnologias': metricas_termonucleares['tecnologias_utilizadas']
    })
    
    # Actualizar estado del pedido en DB
    try:
        db_manager.update_pedido_final(
            pedido_id=pedido_info['pedido_data']['pedido_id'],
            rider_id=h3_data['selected_rider']['id'],
            eta_minutos=int(routing_data['ruta_completa']['tiempo_total_minutos']),
            cliente_lat=coords_data['cliente']['lat'],
            cliente_lon=coords_data['cliente']['lon'],
            cliente_h3=h3_data['cliente_h3']
        )
    except Exception as e:
        webinar_logger.logger.error(f"❌ Error actualizando pedido final: {e}")
    
    webinar_logger.log_technology_stack_reveal(
        metricas_termonucleares['tecnologias_utilizadas'],
        f"Pedido de {pedido_info['pedido_data']['cliente_nombre']}"
    )
    
    return {
        'procesamiento_completado': True,
        'metricas_finales': metricas_termonucleares,
        'webinar_ready': True,
        'tecnologias_demostradas': len(metricas_termonucleares['tecnologias_utilizadas']),
        'complejidad_revelada': 'TERMONUCLEAR 🚀💥',
        'demo_exitoso': True
    }


# =============================================================================
# DEFINICIÓN DE OPERATORS
# =============================================================================

# Task 1: Recepción
task_recepcion = PythonOperator(
    task_id='recepcion_pedido_termonuclear',
    python_callable=task_recepcion_pedido_termonuclear,
    dag=dag
)

# Task 2: Geocoding REAL
task_geocoding = PythonOperator(
    task_id='geocoding_termonuclear',
    python_callable=task_geocoding_termonuclear,
    dag=dag
)

# Task 3: Análisis H3 + Riders
task_h3_analysis = PythonOperator(
    task_id='analisis_h3_termonuclear',
    python_callable=task_analisis_h3_termonuclear,
    dag=dag
)

# Task 4: Trazado rutas H3
task_rutas_h3 = PythonOperator(
    task_id='trazado_rutas_h3',
    python_callable=task_trazado_rutas_h3,
    dag=dag
)

# Task 5: Preparación extracción OSM
task_prep_osm = PythonOperator(
    task_id='preparacion_extraccion_osm',
    python_callable=task_preparacion_extraccion_osm,
    dag=dag
)

# Task 6: Extracción OSM REAL
task_osm_extraction = PythonOperator(
    task_id='extraccion_osm_termonuclear',
    python_callable=task_extraccion_osm_termonuclear,
    dag=dag
)

# Task 7: Almacenamiento PostGIS
task_postgis_storage = PythonOperator(
    task_id='almacenamiento_postgis',
    python_callable=task_almacenamiento_postgis,
    dag=dag
)

# Task 8: Routing Dijkstra REAL
task_routing = PythonOperator(
    task_id='routing_dijkstra_termonuclear',
    python_callable=task_routing_dijkstra_termonuclear,
    dag=dag
)

# Task 9: Tracking vectorial
task_tracking = PythonOperator(
    task_id='tracking_vectorial',
    python_callable=task_tracking_vectorial,
    dag=dag
)

# Task 10: Notificaciones progresivas
task_notifications = PythonOperator(
    task_id='notificaciones_progresivas',
    python_callable=task_notificaciones_progresivas,
    dag=dag
)

# Task 11: Finalización épica
task_finalizacion = PythonOperator(
    task_id='finalizacion_termonuclear',
    python_callable=task_finalizacion_termonuclear,
    dag=dag
)

# =============================================================================
# DEPENDENCIAS DEL PIPELINE TERMONUCLEAR
# =============================================================================

# Flow secuencial que revela cada capa de complejidad espacial
task_recepcion >> task_geocoding >> task_h3_analysis >> task_rutas_h3

# Preparación y extracción OSM
task_rutas_h3 >> task_prep_osm >> task_osm_extraction

# Almacenamiento y routing
task_osm_extraction >> task_postgis_storage >> task_routing

# Tracking y notificaciones
task_routing >> task_tracking >> task_notifications

# Finalización épica
task_notifications >> task_finalizacion

# =============================================================================
# DOCUMENTACIÓN PARA WEBINAR GEODOJO
# =============================================================================

dag.doc_md = """
# 🚀💥 RutIA DAG TERMONUCLEAR 💥🚀

## 🎯 PROPÓSITO DEL WEBINAR GeoDojo:
Revelar que cada "pedido simple" ejecuta un **MOTOR ESPACIAL TERMONUCLEAR**

## 🔥 PIPELINE COMPLETO (11 TASKS):
1. **Recepción** → JSON desde n8n → PostgreSQL
2. **Geocoding** → Nominatim REAL sobre dirección del cliente
3. **H3 Analysis** → Sistema hexagonal + riders inteligentes  
4. **Rutas H3** → Trazado hexagonal completo
5. **Prep OSM** → Parámetros para extracción masiva
6. **OSM Extraction** → Overpass API REAL + fallback
7. **PostGIS Storage** → Red vial completa en PostGIS
8. **Routing Dijkstra** → pgRouting REAL sobre calles OSM
9. **Tracking Vectorial** → Sistema de seguimiento matemático
10. **Notificaciones** → Estados progresivos via n8n
11. **Finalización** → Métricas épicas del procesamiento

## 🎬 REVEAL ÉPICO DEL WEBINAR:
**"Pensaste que pediste una hamburguesa... pero ejecutaste un SISTEMA ESPACIAL TERMONUCLEAR"**

### 📱 LO QUE VE EL CLIENTE:
- "Hice un pedido en La Geográfica"
- "Mi pedido está confirmado"
- "El rider viene en camino"

### 🔥 LO QUE REALMENTE EJECUTA:
- ✅ **Nominatim Geocoding** → Dirección real a coordenadas GPS
- ✅ **H3 Hexagonal System** → Análisis espacial con geometría hexagonal
- ✅ **OpenStreetMap Extraction** → Calles reales via Overpass API
- ✅ **PostGIS Spatial Database** → Almacenamiento geométrico optimizado
- ✅ **pgRouting Dijkstra** → Algoritmo de rutas óptimas (mismo que Google Maps)
- ✅ **Tracking Vectorial** → Interpolación matemática en tiempo real
- ✅ **n8n Integration** → Automatización de workflow completo

## 🗺️ TECNOLOGÍAS DEMOSTRADAS:
- **PostgreSQL + PostGIS** → Base de datos espacial enterprise
- **H3 by Uber** → Sistema hexagonal usado por Uber/Lyft/Airbnb
- **OpenStreetMap** → Base de datos geográfica más grande del mundo
- **pgRouting** → Motor de routing con 50+ algoritmos
- **Airflow** → Orchestration de pipelines complejos
- **n8n** → Workflow automation low-code

## 🚀 RESULTADO WEBINAR:
- **Distancia real** calculada metro por metro
- **ETA preciso** usando velocidades reales por tipo de calle  
- **Tracking vectorial** con interpolación matemática
- **Red vial completa** extraída solo para UN pedido

## 💡 MENSAJE CLAVE:
**"SIN PostGIS + H3 + OSM + pgRouting = NO HAY UBER, RAPPI, AIRBNB"**

¡GeoDojo enseña la tecnología REAL detrás de estas apps! 🗺️🔥

---
*Desarrollado para Webinar GeoDojo Septiembre 2025*  
*"Revelando la complejidad espacial oculta del delivery"* 🎬
"""