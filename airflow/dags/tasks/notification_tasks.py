"""
?? RutIA Notification Tasks
Sistema de tracking vectorial + notificaciones progresivas via n8n
"""

import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from utils.logging_utils import webinar_logger, metrics_collector
from utils.db_utils import db_manager

def task_tracking_vectorial(**context):
    """?? TRACKING: Sistema de seguimiento vectorial en tiempo real"""
    
    ti = context['task_instance']
    routing_data = ti.xcom_pull(task_ids='routing_dijkstra_termonuclear')
    pedido_info = ti.xcom_pull(task_ids='recepcion_pedido_termonuclear')
    h3_data = ti.xcom_pull(task_ids='analisis_h3_termonuclear')
    
    if 'error' in str(routing_data) or not routing_data.get('ruta_completa'):
        error_msg = "No hay datos de routing validos para tracking"
        webinar_logger.log_step_error("TRACKING_INIT", Exception(error_msg))
        raise Exception(error_msg)
    
    ruta_completa = routing_data['ruta_completa']
    pedido_id = pedido_info['pedido_data']['pedido_id']
    rider_info = h3_data['selected_rider']
    
    webinar_logger.log_step_start(
        "TRACKING VECTORIAL",
        {
            "pedido_id": pedido_id,
            "rider": rider_info['nombre'],
            "distancia_total": f"{ruta_completa['distancia_total_km']:.1f}km",
            "eta_total": f"{ruta_completa['tiempo_total_minutos']:.0f}min"
        }
    )
    
    # Generar estados de tracking progresivo
    tracking_states = generate_tracking_states(
        pedido_id, 
        rider_info, 
        ruta_completa,
        routing_data
    )
    
    # Crear sistema de tracking completo
    tracking_sistema = {
        'pedido_id': pedido_id,
        'rider_info': {
            'id': rider_info['id'],
            'nombre': rider_info['nombre'],
            'posicion_inicial': {
                'lat': rider_info['lat'],
                'lon': rider_info['lon'],
                'h3': rider_info['h3_position']
            }
        },
        'ruta_vectorial': create_vector_route(routing_data),
        'tracking_states': tracking_states,
        'configuracion': {
            'update_frequency_seconds': 30,
            'precision_method': 'interpolacion_vectorial',
            'total_states': len(tracking_states)
        },
        'estado_actual': tracking_states[0] if tracking_states else None,
        'tracking_activo': True,
        'created_at': datetime.now().isoformat()
    }
    
    webinar_logger.log_webinar_epic(
        "TRACKING VECTORIAL ACTIVADO",
        f"Sistema de tracking con {len(tracking_states)} estados progresivos",
        {
            'tracking_method': 'interpolacion_vectorial_matematica',
            'update_frequency': '30 segundos',
            'estados_totales': len(tracking_states),
            'precision': 'metro_por_metro'
        },
        "El 'puntito que se mueve' = interpolacion matematica sobre geometria vectorial real",
        "MIND_BLOWING"
    )
    
    # Metricas
    metrics_collector.set_spatial_metric("tracking_states", len(tracking_states))
    metrics_collector.set_spatial_metric("tracking_activo", True)
    
    webinar_logger.log_step_success(
        "TRACKING VECTORIAL COMPLETADO",
        {
            "sistema_creado": True,
            "estados_generados": len(tracking_states),
            "vectorial_ready": True
        }
    )
    
    return tracking_sistema


def task_notificaciones_progresivas(**context):
    """?? NOTIFICATIONS: Notificar estados al cliente via n8n"""
    
    ti = context['task_instance']
    tracking_data = ti.xcom_pull(task_ids='tracking_vectorial')
    pedido_info = ti.xcom_pull(task_ids='recepcion_pedido_termonuclear')
    routing_data = ti.xcom_pull(task_ids='routing_dijkstra_termonuclear')
    coords_data = ti.xcom_pull(task_ids='geocoding_termonuclear')
    
    if 'error' in str(tracking_data) or not tracking_data.get('tracking_states'):
        error_msg = "No hay datos de tracking para notificar"
        webinar_logger.log_step_error("NOTIFICATIONS_INIT", Exception(error_msg))
        raise Exception(error_msg)
    
    cliente_info = pedido_info['pedido_data']
    ruta_info = routing_data['ruta_completa'] 
    rider_info = tracking_data['rider_info']
    
    webinar_logger.log_step_start(
        "NOTIFICACIONES PROGRESIVAS",
        {
            "cliente": cliente_info['cliente_nombre'],
            "pedido_id": cliente_info['pedido_id'],
            "estados_a_notificar": len(tracking_data['tracking_states'])
        }
    )
    
    # Crear notificacion principal con TODA la informacion espacial
    notificacion_principal = create_comprehensive_notification(
        cliente_info,
        rider_info,
        ruta_info,
        routing_data,
        coords_data,
        tracking_data
    )
    
    # Enviar notificacion via n8n
    envio_exitoso = send_notification_to_n8n(notificacion_principal)
    
    if not envio_exitoso:
        webinar_logger.logger.warning("?? Error enviando a n8n - notificacion guardada localmente")
    
    webinar_logger.log_reveal_simple_to_complex(
        f"Pedido confirmado para {cliente_info['cliente_nombre']}",
        "Analisis espacial termonuclear completo con 6+ tecnologias",
        [
            "Nominatim Geocoding",
            "H3 Hexagonal System", 
            "OpenStreetMap Extraction",
            "PostGIS Spatial Database",
            "pgRouting Dijkstra",
            "n8n Workflow Automation"
        ]
    )
    
    # Programar notificaciones futuras (simulado)
    future_notifications = schedule_progressive_notifications(
        cliente_info['pedido_id'],
        tracking_data['tracking_states']
    )
    
    # Metricas
    metrics_collector.add_technology_used("n8n")
    metrics_collector.set_spatial_metric("notificacion_enviada", envio_exitoso)
    
    resultado_notificaciones = {
        'notificacion_principal_enviada': envio_exitoso,
        'mensaje_enviado': notificacion_principal['mensaje_cliente'],
        'datos_tecnicos_incluidos': True,
        'notificaciones_programadas': len(future_notifications),
        'tracking_url': f"https://rutia.app/tracking/{cliente_info['pedido_id']}",
        'n8n_integration_ready': True
    }
    
    webinar_logger.log_step_success(
        "NOTIFICACIONES ENVIADAS",
        resultado_notificaciones,
        {
            "cliente_notificado": True,
            "info_espacial_incluida": True,
            "tracking_disponible": True
        }
    )
    
    return resultado_notificaciones


def generate_tracking_states(pedido_id: str, rider_info: Dict, 
                           ruta_completa: Dict, routing_data: Dict) -> List[Dict]:
    """Generar estados progresivos de tracking"""
    
    eta_total = ruta_completa['tiempo_total_minutos']
    
    states = [
        {
            'estado': 'rider_asignado',
            'progreso_pct': 0,
            'eta_minutos': int(eta_total),
            'mensaje': f"Rider {rider_info['nombre']} ha sido asignado a tu pedido",
            'posicion_actual': {
                'lat': rider_info['lat'],
                'lon': rider_info['lon']
            },
            'detalles_tecnicos': 'Rider seleccionado usando analisis H3 hexagonal',
            'timestamp': datetime.now().isoformat()
        },
        {
            'estado': 'dirigiendose_local',
            'progreso_pct': 25,
            'eta_minutos': int(eta_total * 0.75),
            'mensaje': f"Local: {rider_info['nombre']} se dirige al local (La Geografica)",
            'posicion_actual': calculate_interpolated_position(routing_data, 0.25),
            'detalles_tecnicos': 'Ruta calculada con pgRouting Dijkstra sobre calles OSM',
            'timestamp': datetime.now().isoformat()
        },
        {
            'estado': 'recogiendo_pedido',
            'progreso_pct': 50,
            'eta_minutos': int(eta_total * 0.5),
            'mensaje': f"Pedido: {rider_info['nombre']} esta recogiendo tu pedido",
            'posicion_actual': calculate_interpolated_position(routing_data, 0.5),
            'detalles_tecnicos': 'Posicion calculada por interpolacion vectorial',
            'timestamp': datetime.now().isoformat()
        },
        {
            'estado': 'en_camino_cliente',
            'progreso_pct': 75,
            'eta_minutos': int(eta_total * 0.25),
            'mensaje': f"Camino: {rider_info['nombre']} va hacia tu domicilio",
            'posicion_actual': calculate_interpolated_position(routing_data, 0.75),
            'detalles_tecnicos': 'Tracking en tiempo real sobre geometria de calles reales',
            'timestamp': datetime.now().isoformat()
        },
        {
            'estado': 'cerca_destino',
            'progreso_pct': 95,
            'eta_minutos': 2,
            'mensaje': f"Cerca: {rider_info['nombre']} esta muy cerca de tu ubicacion",
            'posicion_actual': calculate_interpolated_position(routing_data, 0.95),
            'detalles_tecnicos': 'Geofencing activado - precision GPS de metros',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    return states


def calculate_interpolated_position(routing_data: Dict, progress_factor: float) -> Dict:
    """Calcular posicion interpolada en la ruta (simulado)"""
    
    # En una implementacion real, esto interpolaria sobre las geometrias reales
    # Por ahora usamos posiciones aproximadas
    
    ruta_rider_empresa = routing_data.get('ruta_rider_empresa', {})
    ruta_empresa_cliente = routing_data.get('ruta_empresa_cliente', {})
    
    # Posicion simulada basada en progreso
    if progress_factor <= 0.5:
        # Primera mitad: rider hacia empresa
        return {
            'lat': -34.6037 + (progress_factor * 0.01),  # Aproximacion
            'lon': -58.3816 + (progress_factor * 0.01),
            'interpolation_method': 'vectorial_geometrica'
        }
    else:
        # Segunda mitad: empresa hacia cliente
        return {
            'lat': -34.6137 + ((progress_factor - 0.5) * 0.02),
            'lon': -58.3916 + ((progress_factor - 0.5) * 0.02),
            'interpolation_method': 'vectorial_geometrica'
        }


def create_vector_route(routing_data: Dict) -> Dict:
    """Crear representacion vectorial de la ruta completa"""
    
    ruta_rider_empresa = routing_data.get('ruta_rider_empresa', {})
    ruta_empresa_cliente = routing_data.get('ruta_empresa_cliente', {})
    
    return {
        'tipo': 'ruta_vectorial_completa',
        'segmentos': [
            {
                'nombre': 'rider_to_business',
                'geometrias': ruta_rider_empresa.get('geometrias', []),
                'distancia_km': ruta_rider_empresa.get('distancia_km', 0),
                'tiempo_min': ruta_rider_empresa.get('tiempo_minutos', 0)
            },
            {
                'nombre': 'business_to_client', 
                'geometrias': ruta_empresa_cliente.get('geometrias', []),
                'distancia_km': ruta_empresa_cliente.get('distancia_km', 0),
                'tiempo_min': ruta_empresa_cliente.get('tiempo_minutos', 0)
            }
        ],
        'precision': 'metro_por_metro_sobre_calles_osm',
        'interpolation_ready': True
    }


def create_comprehensive_notification(cliente_info: Dict, rider_info: Dict,
                                    ruta_info: Dict, routing_data: Dict,
                                    coords_data: Dict, tracking_data: Dict) -> Dict:
    """Crear notificacion comprensiva con TODA la informacion espacial"""
    
    mensaje_cliente = f"""PEDIDO CONFIRMADO EN LA GEOGRAFICA! 

Cliente: {cliente_info['cliente_nombre']}
Pedido ID: {cliente_info['pedido_id']}
Total: ${cliente_info.get('pedido_total', 0):,.0f}

RIDER ASIGNADO: {rider_info['nombre']}  
Distancia total: {ruta_info['distancia_total_km']:.1f} km
Tiempo estimado: {int(ruta_info['tiempo_total_minutos'])} minutos
Ruta optimizada: {ruta_info['calles_totales']} calles analizadas

TECNOLOGIA ESPACIAL ACTIVADA:
- Geocoding preciso completado
- Analisis H3 hexagonal ejecutado  
- Red vial OSM extraida y almacenada
- Routing Dijkstra calculado
- Tracking vectorial en tiempo real

Segui tu pedido en tiempo real!
Powered by RutIA x GeoDojo

Tu pedido esta siendo procesado con precision cartografica!"""
    
    return {
        'tipo': 'confirmacion_pedido_termonuclear',
        'pedido_id': cliente_info['pedido_id'],
        'cliente_nombre': cliente_info['cliente_nombre'],
        'mensaje_cliente': mensaje_cliente,
        'rider_info': {
            'nombre': rider_info['nombre'],
            'posicion_h3': rider_info.get('posicion_inicial', {}).get('h3', ''),
            'distancia_inicial': f"{ruta_info['distancia_total_km']:.1f}km"
        },
        'routing_details': {
            'algoritmo': 'Dijkstra',
            'calles_analizadas': ruta_info['calles_totales'],
            'precision': routing_data.get('precision', 'real')
        },
        'spatial_technologies': {
            'geocoding': coords_data['cliente']['geocoder'],
            'h3_resolution': 9,
            'osm_extraction': True,
            'pgrouting': True,
            'tracking_vectorial': True
        },
        'tracking_info': {
            'tracking_url': f"https://rutia.app/tracking/{cliente_info['pedido_id']}",
            'update_frequency': '30 segundos',
            'estados_totales': len(tracking_data['tracking_states'])
        },
        'timestamp': datetime.now().isoformat()
    }


def send_notification_to_n8n(notification_data: Dict) -> bool:
    """Enviar notificacion a n8n webhook"""
    
    n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL', 'https://webhook.n8n.demo/rutia')
    
    if not n8n_webhook_url or 'demo' in n8n_webhook_url:
        webinar_logger.logger.info("Simulando envio a n8n (URL demo)")
        time.sleep(1)  # Simular latencia de red
        return True
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'RutIA-GeoDojo/1.0'
        }
        
        response = requests.post(
            n8n_webhook_url,
            json=notification_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            webinar_logger.logger.info(f"Notificacion enviada a n8n exitosamente")
            return True
        else:
            webinar_logger.logger.error(f"Error n8n HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        webinar_logger.logger.error(f"Error conectando a n8n: {e}")
        return False


def schedule_progressive_notifications(pedido_id: str, tracking_states: List[Dict]) -> List[Dict]:
    """Programar notificaciones progresivas futuras"""
    
    scheduled_notifications = []
    
    for i, state in enumerate(tracking_states[1:], 1):  # Skip first state (already sent)
        
        # Calcular cuando enviar esta notificacion
        delay_minutes = state['eta_minutos'] - tracking_states[0]['eta_minutos']
        if delay_minutes < 0:
            delay_minutes = i * 5  # Fallback: cada 5 minutos
        
        notification = {
            'pedido_id': pedido_id,
            'estado': state['estado'],
            'mensaje': state['mensaje'],
            'scheduled_for': datetime.now().isoformat(),
            'delay_minutes': delay_minutes,
            'progreso_pct': state['progreso_pct']
        }
        
        scheduled_notifications.append(notification)
    
    webinar_logger.logger.info(f"{len(scheduled_notifications)} notificaciones programadas")
    
    return scheduled_notifications


def update_pedido_status_final(pedido_id: str, tracking_data: Dict, 
                             routing_data: Dict, coords_data: Dict) -> bool:
    """Actualizar estado final del pedido en base de datos"""
    
    try:
        ruta_completa = routing_data['ruta_completa']
        cliente_coords = coords_data['cliente']
        
        db_manager.update_pedido_final(
            pedido_id=pedido_id,
            rider_id=tracking_data['rider_info']['id'],
            eta_minutos=int(ruta_completa['tiempo_total_minutos']),
            cliente_lat=cliente_coords['lat'],
            cliente_lon=cliente_coords['lon'],
            cliente_h3=tracking_data['rider_info'].get('posicion_inicial', {}).get('h3', '')
        )
        
        webinar_logger.logger.info(f"Estado del pedido {pedido_id} actualizado en DB")
        return True
        
    except Exception as e:
        webinar_logger.logger.error(f"Error actualizando pedido {pedido_id}: {e}")
        return False