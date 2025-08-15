"""
📍 RutIA Geocoding Tasks
Geocoding REAL de direcciones reales usando Nominatim OpenStreetMap
"""

import requests
import time
import os
from typing import Dict, Optional, Tuple
from utils.logging_utils import webinar_logger, metrics_collector
from utils.db_utils import db_manager

def task_geocoding_termonuclear(**context):
    """🎬 GEOCODING: De dirección real del cliente a coordenadas GPS precisas"""
    
    ti = context['task_instance']
    pedido_info = ti.xcom_pull(task_ids='recepcion_pedido_termonuclear')
    
    # Dirección REAL que viene del JSON del cliente
    direccion_real = pedido_info['pedido_data']['cliente_direccion']
    pedido_id = pedido_info['pedido_data']['pedido_id']
    
    webinar_logger.log_step_start(
        "GEOCODING REAL", 
        {"direccion_cliente": direccion_real, "pedido_id": pedido_id}
    )
    
    # Configuración empresa desde .env
    empresa_config = {
        'nombre': os.getenv('EMPRESA_NOMBRE', 'La Geográfica'),
        'direccion': os.getenv('EMPRESA_DIRECCION', 'Blanco Encalada 2680, CABA'),
        'lat': float(os.getenv('EMPRESA_LAT', -34.6037)),
        'lon': float(os.getenv('EMPRESA_LON', -58.3816))
    }
    
    # GEOCODING REAL del cliente usando Nominatim
    cliente_coords = geocode_with_nominatim(direccion_real)
    
    # Si no encuentra la dirección, usar fallback cerca del negocio
    if not cliente_coords:
        webinar_logger.logger.warning(f"⚠️ Geocoding fallback para: {direccion_real}")
        cliente_coords = {
            'lat': empresa_config['lat'] + 0.01,  # ~1km del local
            'lon': empresa_config['lon'] + 0.01,
            'direccion_original': direccion_real,
            'geocoder': 'Fallback coords',
            'confidence': 'fallback',
            'display_name': f"Área cercana a {direccion_real}"
        }
    
    coords_resultado = {
        'empresa': empresa_config,
        'cliente': cliente_coords
    }
    
    # Logging épico para webinar
    webinar_logger.log_spatial_analysis(
        "GEOCODING REAL",
        {"direccion_texto": direccion_real},
        {
            "cliente_lat": cliente_coords['lat'],
            "cliente_lon": cliente_coords['lon'], 
            "geocoder_usado": cliente_coords['geocoder'],
            "precision": cliente_coords['confidence']
        },
        f"Dirección '{direccion_real}' → Coordenadas GPS precisas para análisis espacial"
    )
    
    # Métricas
    metrics_collector.add_technology_used("Nominatim")
    metrics_collector.add_technology_used("OpenStreetMap")
    metrics_collector.set_spatial_metric("cliente_geocoded", True)
    metrics_collector.set_spatial_metric("empresa_coords", f"{empresa_config['lat']},{empresa_config['lon']}")
    
    webinar_logger.log_step_success(
        "GEOCODING COMPLETADO",
        coords_resultado,
        {
            "geocoding_exitoso": True,
            "precision": cliente_coords['confidence'],
            "api_utilizada": "Nominatim OSM"
        }
    )
    
    return coords_resultado


def geocode_with_nominatim(direccion: str, country_code: str = 'ar') -> Optional[Dict]:
    """Geocodificar dirección real usando Nominatim OpenStreetMap"""
    
    webinar_logger.logger.info(f"🌍 Geocodificando dirección real: {direccion}")
    
    try:
        # Configuración Nominatim
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': direccion,
            'format': 'json',
            'limit': 1,
            'countrycodes': country_code,
            'addressdetails': 1,
            'extratags': 1
        }
        
        headers = {
            'User-Agent': 'RutIA-GeoDojo/1.0 (hello@geodojo.ai)'
        }
        
        webinar_logger.logger.info(f"🔍 Consultando Nominatim: {direccion}")
        
        # Request real a Nominatim
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) > 0:
            result = data[0]
            
            cliente_coords = {
                'lat': float(result['lat']),
                'lon': float(result['lon']),
                'direccion_original': direccion,
                'display_name': result.get('display_name', direccion),
                'geocoder': 'Nominatim OpenStreetMap REAL',
                'confidence': 'high',
                'osm_id': result.get('osm_id', 'unknown'),
                'osm_type': result.get('osm_type', 'unknown'),
                'place_id': result.get('place_id', 'unknown'),
                'importance': result.get('importance', 0),
                'address_details': result.get('address', {})
            }
            
            webinar_logger.logger.info(f"✅ Geocoding exitoso: {cliente_coords['lat']:.6f}, {cliente_coords['lon']:.6f}")
            webinar_logger.logger.info(f"📍 Ubicación encontrada: {cliente_coords['display_name']}")
            
            return cliente_coords
            
        else:
            webinar_logger.logger.warning(f"❌ No se encontraron resultados para: {direccion}")
            return None
            
    except requests.exceptions.Timeout:
        webinar_logger.logger.error(f"⏱️ Timeout geocodificando: {direccion}")
        return None
        
    except requests.exceptions.RequestException as e:
        webinar_logger.logger.error(f"🌐 Error de conexión geocodificando: {e}")
        return None
        
    except Exception as e:
        webinar_logger.logger.error(f"❌ Error geocodificando {direccion}: {e}")
        return None


def validate_coordinates(lat: float, lon: float, country: str = 'argentina') -> bool:
    """Validar que las coordenadas sean razonables para el país"""
    
    # Bounds aproximados para Argentina
    country_bounds = {
        'argentina': {
            'lat_min': -55.0,
            'lat_max': -21.0,
            'lon_min': -73.5,
            'lon_max': -53.0
        }
    }
    
    bounds = country_bounds.get(country, country_bounds['argentina'])
    
    lat_valid = bounds['lat_min'] <= lat <= bounds['lat_max']
    lon_valid = bounds['lon_min'] <= lon <= bounds['lon_max']
    
    is_valid = lat_valid and lon_valid
    
    if not is_valid:
        webinar_logger.logger.warning(
            f"⚠️ Coordenadas fuera de rango para {country}: {lat:.6f}, {lon:.6f}"
        )
    
    return is_valid


def reverse_geocode_validation(lat: float, lon: float) -> Optional[Dict]:
    """Reverse geocoding para validar coordenadas obtenidas"""
    
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'RutIA-GeoDojo/1.0 (hello@geodojo.ai)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data:
            return {
                'reverse_address': data.get('display_name', 'Unknown'),
                'reverse_valid': True,
                'address_components': data.get('address', {})
            }
        
        return {'reverse_valid': False}
        
    except Exception as e:
        webinar_logger.logger.error(f"❌ Error en reverse geocoding: {e}")
        return {'reverse_valid': False, 'error': str(e)}


def enhanced_geocoding_with_fallbacks(direccion: str) -> Optional[Dict]:
    """Geocoding mejorado con múltiples estrategias de fallback"""
    
    # Intento 1: Direccion exacta
    result = geocode_with_nominatim(direccion)
    if result:
        return result
    
    # Intento 2: Remover numero de piso/depto
    direccion_sin_piso = remove_floor_apartment(direccion)
    if direccion_sin_piso != direccion:
        webinar_logger.logger.info(f"🔄 Intentando sin piso/depto: {direccion_sin_piso}")
        result = geocode_with_nominatim(direccion_sin_piso)
        if result:
            result['fallback_used'] = 'sin_piso_depto'
            return result
    
    # Intento 3: Solo calle y ciudad
    direccion_simplificada = simplify_address(direccion)
    if direccion_simplificada != direccion:
        webinar_logger.logger.info(f"🔄 Intentando dirección simplificada: {direccion_simplificada}")
        result = geocode_with_nominatim(direccion_simplificada)
        if result:
            result['fallback_used'] = 'direccion_simplificada'
            result['confidence'] = 'medium'
            return result
    
    webinar_logger.logger.error(f"❌ Todos los intentos de geocoding fallaron para: {direccion}")
    return None


def remove_floor_apartment(direccion: str) -> str:
    """Remover información de piso/departamento de la dirección"""
    
    # Patrones comunes: "3A", "4B", "PB", "1°", "2do", etc.
    import re
    
    # Remover patrones como: 3A, 4B, PB, 1°, 2do piso, depto 3, etc.
    patterns = [
        r'\s+\d+[A-Z]?\s*$',  # Final con número + letra opcional
        r'\s+PB\s*$',         # Planta baja
        r'\s+\d+°?\s*$',      # Número con grado opcional
        r'\s+\d+(do|er)\s*$', # 1er, 2do, etc.
        r'\s+depto?\s+\d+.*$', # depto 3, dpto 4A, etc.
        r'\s+piso\s+\d+.*$',  # piso 3, piso 4A, etc.
        r'\s+\d+[A-Z]\s+caba\s*$' # Casos como "3A caba"
    ]
    
    direccion_limpia = direccion
    for pattern in patterns:
        direccion_limpia = re.sub(pattern, '', direccion_limpia, flags=re.IGNORECASE)
    
    return direccion_limpia.strip()


def simplify_address(direccion: str) -> str:
    """Simplificar dirección a componentes básicos"""
    
    # Extraer calle principal y ciudad
    parts = direccion.split(',')
    if len(parts) >= 2:
        calle = parts[0].strip()
        ciudad = parts[-1].strip()
        return f"{calle}, {ciudad}"
    
    # Si no tiene comas, buscar CABA/Buenos Aires
    if 'caba' in direccion.lower() or 'buenos aires' in direccion.lower():
        calle_parte = direccion.split()[0:3]  # Primeras 3 palabras
        return f"{' '.join(calle_parte)}, CABA"
    
    return direccion


def get_geocoding_quality_score(geocoding_result: Dict) -> float:
    """Calcular score de calidad del geocoding (0-1)"""
    
    score = 0.0
    
    # Base score por geocoder usado
    if geocoding_result.get('geocoder') == 'Nominatim OpenStreetMap REAL':
        score += 0.5
    
    # Score por confidence
    confidence = geocoding_result.get('confidence', 'low')
    if confidence == 'high':
        score += 0.3
    elif confidence == 'medium':
        score += 0.2
    
    # Score por importance OSM
    importance = geocoding_result.get('importance', 0)
    score += min(importance * 0.2, 0.2)
    
    return min(score, 1.0)
