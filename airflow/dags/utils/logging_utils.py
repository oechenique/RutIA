"""
🎬 RutIA Webinar Logging Utilities
Sistema de logging épico para revelar la complejidad espacial en el webinar
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

class WebinarLogger:
    """Logger épico para webinar GeoDojo"""
    
    def __init__(self, logger_name: str = 'rutia_termonuclear'):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Si no tiene handlers, agregar uno
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_webinar_epic(self, step_name: str, description: str, 
                        data: Dict = None, reveal: str = None, 
                        complexity_level: str = "NORMAL"):
        """Logger épico para pasos del webinar con revelaciones"""
        
        # Header épico basado en complejidad
        complexity_symbols = {
            "NORMAL": "🔧",
            "TERMONUCLEAR": "💥🚀",
            "MIND_BLOWING": "🤯💫",
            "SPATIAL_MAGIC": "🗺️✨"
        }
        
        symbol = complexity_symbols.get(complexity_level, "🔧")
        
        self.logger.info("=" * 80)
        self.logger.info(f"{symbol} WEBINAR STEP: {step_name}")
        self.logger.info(f"📝 {description}")
        
        if data:
            # Pretty print data para el webinar
            data_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            self.logger.info(f"📊 Data:\n{data_str}")
        
        if reveal:
            self.logger.info(f"🎯 WEBINAR REVEAL: {reveal}")
        
        self.logger.info("=" * 80)
    
    def log_step_start(self, step_name: str, input_data: Dict = None):
        """Log inicio de paso"""
        self.logger.info(f"🚀 INICIANDO: {step_name}")
        if input_data:
            self.logger.info(f"📥 Input: {json.dumps(input_data, default=str)}")
    
    def log_step_success(self, step_name: str, output_data: Dict = None, 
                        metrics: Dict = None):
        """Log éxito de paso"""
        self.logger.info(f"✅ COMPLETADO: {step_name}")
        if output_data:
            self.logger.info(f"📤 Output: {json.dumps(output_data, default=str)}")
        if metrics:
            self.logger.info(f"📈 Métricas: {json.dumps(metrics, default=str)}")
    
    def log_step_error(self, step_name: str, error: Exception, 
                      context: Dict = None):
        """Log error de paso"""
        self.logger.error(f"❌ ERROR EN: {step_name}")
        self.logger.error(f"💀 Error: {str(error)}")
        if context:
            self.logger.error(f"🔍 Contexto: {json.dumps(context, default=str)}")
    
    def log_reveal_simple_to_complex(self, simple_action: str, 
                                   complex_reality: str, 
                                   technologies_used: list):
        """Log para revelación 'simple → complejo'"""
        self.log_webinar_epic(
            "REVELACIÓN ÉPICA",
            f"Lo que el cliente ve: '{simple_action}'",
            {
                "realidad_compleja": complex_reality,
                "tecnologias_involucradas": technologies_used,
                "nivel_complejidad": "TERMONUCLEAR"
            },
            f"DETRÁS DE '{simple_action}' → {complex_reality}",
            "MIND_BLOWING"
        )
    
    def log_spatial_analysis(self, analysis_type: str, input_coords: Dict, 
                           h3_data: Dict, impact: str):
        """Log para análisis espacial"""
        self.log_webinar_epic(
            f"ANÁLISIS ESPACIAL: {analysis_type}",
            "Conversión de coordenadas simples a sistema hexagonal H3",
            {
                "coordenadas_input": input_coords,
                "h3_resultado": h3_data,
                "precision": "~174 metros por hexágono",
                "sistema": "H3 Uber Technologies"
            },
            impact,
            "SPATIAL_MAGIC"
        )
    
    def log_osm_extraction(self, hexagon_count: int, ways_extracted: int, 
                          area_km2: float, bbox: Dict):
        """Log para extracción OSM"""
        self.log_webinar_epic(
            "EXTRACCIÓN OSM MASIVA",
            f"Extracción de red vial OpenStreetMap para {hexagon_count} hexágonos",
            {
                "hexagonos_procesados": hexagon_count,
                "calles_extraidas": ways_extracted,
                "area_cubierta_km2": round(area_km2, 2),
                "bounding_box": bbox,
                "api_utilizada": "Overpass API"
            },
            f"UN pedido simple → {ways_extracted} calles extraídas de OSM",
            "TERMONUCLEAR"
        )
    
    def log_pgrouting_analysis(self, route_info: Dict, algorithm: str = "Dijkstra"):
        """Log para análisis pgRouting"""
        self.log_webinar_epic(
            f"ROUTING REAL - {algorithm.upper()}",
            f"Cálculo de rutas óptimas usando {algorithm} sobre red vial real",
            {
                "algoritmo": algorithm,
                "distancia_total_km": route_info.get("distancia_total_km", 0),
                "tiempo_total_min": route_info.get("tiempo_total_min", 0),
                "calles_utilizadas": route_info.get("calles_utilizadas", 0),
                "precision": "metro_por_metro_sobre_calles_reales"
            },
            f"Routing {algorithm} = mismo algoritmo que usa Google Maps",
            "SPATIAL_MAGIC"
        )
    
    def log_technology_stack_reveal(self, technologies: list, 
                                  simple_user_action: str):
        """Log para revelar stack tecnológico completo"""
        tech_descriptions = {
            "PostgreSQL": "Base de datos espacial para geometrías",
            "PostGIS": "Extensión espacial con +300 funciones GIS",
            "H3": "Sistema hexagonal de Uber Technologies",
            "pgRouting": "Motor de routing con algoritmos como Dijkstra",
            "OSM": "Base de datos geográfica más grande del mundo",
            "Nominatim": "Geocodificador basado en OpenStreetMap",
            "Overpass API": "API para consultas complejas a OpenStreetMap"
        }
        
        tech_details = {}
        for tech in technologies:
            tech_details[tech] = tech_descriptions.get(tech, f"Tecnología: {tech}")
        
        self.log_webinar_epic(
            "STACK TECNOLÓGICO COMPLETO",
            f"Tecnologías activadas por: '{simple_user_action}'",
            {
                "accion_usuario": simple_user_action,
                "tecnologias_activadas": tech_details,
                "complejidad_oculta": "TERMONUCLEAR"
            },
            f"Sin estas {len(technologies)} tecnologías = NO HAY delivery moderno",
            "MIND_BLOWING"
        )
    
    def log_final_metrics(self, processing_metrics: Dict):
        """Log métricas finales del procesamiento"""
        self.log_webinar_epic(
            "🎉 PROCESAMIENTO TERMONUCLEAR COMPLETADO 🎉",
            "Pipeline espacial completo ejecutado exitosamente",
            processing_metrics,
            "LO QUE PARECE UN PEDIDO SIMPLE = MOTOR ESPACIAL COMPLEJO",
            "MIND_BLOWING"
        )
        
        # Mensaje final épico
        final_message = f"""
🚀💥 === RUTIA TERMONUCLEAR COMPLETADO === 💥🚀

📱 LO QUE VIO EL CLIENTE:
"Hice un pedido de hamburguesa en La Geográfica"

🔥 LO QUE REALMENTE EJECUTÓ:
✅ Geocoding preciso con Nominatim
✅ {processing_metrics.get('hexagonos_analizados', 0)} hexágonos H3 analizados
✅ {processing_metrics.get('calles_extraidas', 0)} calles OSM extraídas
✅ Red vial completa en PostGIS  
✅ Routing Dijkstra en {processing_metrics.get('area_km2', 0):.1f} km²
✅ Tracking vectorial en tiempo real
✅ {len(processing_metrics.get('tecnologias', []))} tecnologías espaciales

💫 RESULTADO: 
📍 Ruta óptima de {processing_metrics.get('distancia_km', 0):.1f}km 
⏱️ ETA: {processing_metrics.get('eta_minutos', 0)} minutos
🛵 Rider: {processing_metrics.get('rider_nombre', 'Carlos')}

🎯 WEBINAR REVEAL:
"SIN PostGIS + H3 + OSM + pgRouting = NO HAY UBER, RAPPI, AIRBNB"

¡GeoDojo enseña la tecnología REAL detrás de estas apps! 🗺️🔥
"""
        
        self.logger.info(final_message)


class MetricsCollector:
    """Colector de métricas para análisis del webinar"""
    
    def __init__(self):
        self.metrics = {
            'start_time': datetime.now(),
            'steps_completed': [],
            'technologies_used': set(),
            'spatial_analysis': {},
            'performance': {}
        }
    
    def add_step_completion(self, step_name: str, duration_seconds: float, 
                          data: Dict = None):
        """Agregar paso completado"""
        self.metrics['steps_completed'].append({
            'step': step_name,
            'duration_seconds': duration_seconds,
            'timestamp': datetime.now(),
            'data': data or {}
        })
    
    def add_technology_used(self, technology: str):
        """Agregar tecnología utilizada"""
        self.metrics['technologies_used'].add(technology)
    
    def set_spatial_metric(self, key: str, value: Any):
        """Establecer métrica espacial"""
        self.metrics['spatial_analysis'][key] = value
    
    def set_performance_metric(self, key: str, value: Any):
        """Establecer métrica de performance"""
        self.metrics['performance'][key] = value
    
    def get_final_metrics(self) -> Dict:
        """Obtener métricas finales para el webinar"""
        end_time = datetime.now()
        total_duration = (end_time - self.metrics['start_time']).total_seconds()
        
        return {
            'total_duration_seconds': total_duration,
            'steps_completed': len(self.metrics['steps_completed']),
            'technologies_used': list(self.metrics['technologies_used']),
            'spatial_analysis': self.metrics['spatial_analysis'],
            'performance': self.metrics['performance'],
            'complexity_level': 'TERMONUCLEAR',
            'webinar_ready': True
        }


# Instancias globales para usar en tasks
webinar_logger = WebinarLogger()
metrics_collector = MetricsCollector()
