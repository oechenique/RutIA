"""
RutIA Dashboard - Interfaz Visual Principal
Tracking en tiempo real estilo Rappi/PedidosYa desde el lado del cliente

Características:
- Simulador de pedidos con WhatsApp/Telegram
- Mapa tracking en tiempo real
- Rider moviéndose por ruta PostGIS
- Estado del pedido live
- Queries espaciales mostradas en vivo
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
import time
import json
import h3
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
import uuid

# Configuración página
st.set_page_config(
    page_title="RutIA - Tracking Live", 
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para look moderno
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 1rem;
    }
    .status-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .rider-card {
        background: #f8fafc;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .tracking-status {
        font-size: 1.2rem;
        font-weight: 600;
        color: #059669;
    }
</style>
""", unsafe_allow_html=True)

# Configuración API
API_BASE_URL = "http://localhost:3000"

def get_empresa_config():
    """Obtener configuración empresa desde .env o defaults"""
    return {
        'nombre': os.getenv('EMPRESA_NOMBRE', 'RutIA Demo'),
        'lat': float(os.getenv('EMPRESA_LAT', -34.6037)),
        'lon': float(os.getenv('EMPRESA_LON', -58.3816)),
        'direccion': os.getenv('EMPRESA_DIRECCION', 'Blanco Encalada 2680, CABA')
    }

def call_api(endpoint: str, method: str = "GET", data: dict = None):
    """Llamar API RutIA con manejo de errores"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 Error conectando API: {e}")
        return None

def crear_mapa_tracking(empresa_config, riders_data, pedido_tracking=None):
    """Crear mapa principal con tracking"""
    
    # Centrar mapa en empresa
    mapa = folium.Map(
        location=[empresa_config['lat'], empresa_config['lon']],
        zoom_start=14,
        tiles='OpenStreetMap',
        attr='RutIA - Ruteo Inteligente'
    )
    
    # 🏪 Marcador empresa/tienda
    folium.Marker(
        [empresa_config['lat'], empresa_config['lon']],
        popup=f"🏪 {empresa_config['nombre']}<br>{empresa_config['direccion']}",
        tooltip="Tienda",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(mapa)
    
    # 🛵 Riders disponibles
    for rider in riders_data:
        color = 'blue' if rider.get('tiene_pedido_cerca_local') else 'green'
        icon_name = 'motorcycle' if rider.get('pedidos_activos', 0) > 0 else 'user'
        
        folium.Marker(
            [rider['lat'], rider['lon']],
            popup=f"🛵 {rider['nombre']}<br>Estado: {rider['status']}<br>Pedidos: {rider['pedidos_activos']}",
            tooltip=rider['nombre'],
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(mapa)
        
        # Hexágono H3 del rider
        try:
            hex_boundary = h3.h3_to_geo_boundary(rider['h3_actual'], geo_json=True)
            folium.Polygon(
                locations=hex_boundary,
                color=color,
                weight=2,
                fillOpacity=0.1,
                popup=f"H3: {rider['h3_actual']}"
            ).add_to(mapa)
        except:
            pass
    
    # 📍 Si hay tracking activo, mostrar destino y ruta
    if pedido_tracking and pedido_tracking.get('ubicacion_actual'):
        destino_coords = pedido_tracking.get('destino_coords')
        rider_coords = [
            pedido_tracking['ubicacion_actual']['lat'],
            pedido_tracking['ubicacion_actual']['lon']
        ]
        
        # Marcador destino cliente
        if destino_coords:
            folium.Marker(
                destino_coords,
                popup="📍 Tu dirección<br>Destino de entrega",
                tooltip="Destino",
                icon=folium.Icon(color='orange', icon='flag', prefix='fa')
            ).add_to(mapa)
            
            # Línea de ruta (simulada)
            folium.PolyLine(
                locations=[rider_coords, destino_coords],
                color='red',
                weight=4,
                opacity=0.8,
                popup="🛣️ Ruta calculada con PostGIS"
            ).add_to(mapa)
        
        # Centrar en el tracking
        mapa.location = rider_coords
        mapa.zoom_start = 15
    
    return mapa

def simular_pedido_whatsapp():
    """Simulador de pedido estilo WhatsApp"""
    st.markdown("### 📱 Simular Pedido WhatsApp/Telegram")
    
    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Input estilo chat
            mensaje = st.text_area(
                "💬 Escribí tu pedido:",
                value="Una hamburguesa gisera a Blanco Encalada 2750, CABA",
                height=100,
                help="Ejemplo: 'Pizza espacial a Santa Fe 1500, CABA'"
            )
            
            telefono = st.text_input(
                "📞 Tu teléfono:",
                value="+5491123456789"
            )
        
        with col2:
            st.markdown("**Mensajes de ejemplo:**")
            st.code("🍔 Hamburguesa gisera a [tu dirección]")
            st.code("🍕 Pizza espacial a [tu dirección]") 
            st.code("🥟 6 empanadas a [tu dirección]")
    
    if st.button("🚀 ENVIAR PEDIDO", type="primary", use_container_width=True):
        with st.spinner("🧠 Procesando pedido con IA espacial..."):
            
            # Parsear mensaje (simulado)
            if "hamburguesa" in mensaje.lower():
                producto = "Hamburguesa Gisera"
            elif "pizza" in mensaje.lower():
                producto = "Pizza Espacial"
            elif "empanada" in mensaje.lower():
                producto = "Empanadas H3"
            else:
                producto = "Producto Especial"
            
            # Extraer dirección (regex simple)
            import re
            direccion_match = re.search(r'a\s+([^,]+(?:,\s*\w+)*)', mensaje)
            direccion = direccion_match.group(1) if direccion_match else "Blanco Encalada 2750, CABA"
            
            # Llamar API
            pedido_data = {
                "producto": producto,
                "direccion": direccion,
                "telefono": telefono,
                "cliente_nombre": "Cliente Demo",
                "mensaje_original": mensaje
            }
            
            resultado = call_api("/api/pedido", "POST", pedido_data)
            
            if resultado:
                st.success("✅ ¡Pedido enviado exitosamente!")
                
                # Mostrar respuesta estilo WhatsApp
                st.markdown(f"""
                <div class="status-card">
                    <h3>🎉 Respuesta RutIA</h3>
                    <p>{resultado.get('mensaje_cliente', 'Pedido procesado correctamente')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Guardar en session state para tracking
                st.session_state.pedido_actual = resultado
                st.session_state.tracking_activo = True
                
                st.rerun()
            else:
                st.error("❌ Error procesando pedido")

def mostrar_tracking_activo():
    """Mostrar tracking del pedido activo"""
    if not st.session_state.get('tracking_activo') or not st.session_state.get('pedido_actual'):
        return None
    
    pedido_info = st.session_state.pedido_actual
    pedido_id = pedido_info.get('pedido_id')
    
    # Consultar tracking actual
    tracking_data = call_api(f"/api/tracking/{pedido_id}")
    
    if not tracking_data:
        return None
    
    # Header del tracking
    st.markdown(f"""
    <div class="tracking-status">
        🚛 Tu pedido está {tracking_data.get('status', 'en proceso')}
    </div>
    """, unsafe_allow_html=True)
    
    # Info del rider
    rider = tracking_data.get('rider')
    if rider:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🛵 Rider", rider['nombre'])
        
        with col2:
            eta = tracking_data.get('eta_minutos', 20)
            st.metric("⏱️ ETA", f"{eta} min")
        
        with col3:
            progreso = tracking_data.get('progreso_porcentaje', 0)
            st.metric("📊 Progreso", f"{progreso}%")
        
        # Barra de progreso visual
        st.progress(progreso / 100)
        
        # Estados del pedido
        estados = {
            'pendiente': {'icon': '📋', 'text': 'Pedido recibido', 'active': True},
            'asignado': {'icon': '🛵', 'text': 'Rider asignado', 'active': True},
            'recogiendo': {'icon': '📦', 'text': 'Recogiendo pedido', 'active': tracking_data['status'] in ['recogiendo', 'en_camino', 'entregado']},
            'en_camino': {'icon': '🚗', 'text': 'En camino a tu casa', 'active': tracking_data['status'] in ['en_camino', 'entregado']},
            'entregado': {'icon': '✅', 'text': '¡Entregado!', 'active': tracking_data['status'] == 'entregado'}
        }
        
        cols = st.columns(len(estados))
        for i, (estado, info) in enumerate(estados.items()):
            with cols[i]:
                color = "🟢" if info['active'] else "⚪"
                st.markdown(f"{color} {info['icon']}<br>{info['text']}", unsafe_allow_html=True)
    
    return tracking_data

def mostrar_metricas_sistema():
    """Mostrar métricas del sistema"""
    metricas = call_api("/api/metricas")
    
    if not metricas:
        return
    
    st.markdown("### 📊 Estado del Sistema")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🛵 Riders Online", 
            metricas.get('riders_online', 0)
        )
    
    with col2:
        st.metric(
            "📦 Pedidos Activos", 
            metricas.get('pedidos_activos', 0)
        )
    
    with col3:
        st.metric(
            "⏱️ Tiempo Promedio", 
            f"{metricas.get('tiempo_promedio_minutos', 25):.0f} min"
        )
    
    with col4:
        st.metric(
            "🔄 Eficiencia Batching", 
            f"{metricas.get('eficiencia_batching', 0):.1f}%"
        )

def mostrar_queries_espaciales():
    """Mostrar las queries espaciales en acción"""
    with st.expander("🔍 Ver las Queries Espaciales en Acción", expanded=False):
        
        tab1, tab2, tab3 = st.tabs(["Buscar Rider", "Batching", "Routing"])
        
        with tab1:
            st.markdown("**Query que busca el rider perfecto:**")
            st.code("""
-- 🎯 Selección inteligente con scoring de batching
WITH riders_disponibles AS (
    SELECT r.*, 
           h3_distance(r.h3_actual, 'cliente_h3') as distancia,
           r.tiene_pedido_cerca_local
    FROM riders r
    WHERE r.status = 'disponible'
      AND 'cliente_h3' = ANY(r.h3_cobertura)
),
riders_scoring AS (
    SELECT *,
        CASE 
            WHEN tiene_pedido_cerca_local THEN 100 -- 🔥 PRIORIDAD BATCHING
            ELSE 50 - (distancia * 10)
        END as eficiencia_score
    FROM riders_disponibles
)
SELECT * FROM riders_scoring 
ORDER BY eficiencia_score DESC LIMIT 1;
            """, language="sql")
            
            st.info("🤯 **Esta query prioriza riders que ya tienen entregas cerca del local = batching automático!**")
        
        with tab2:
            st.markdown("**Detección automática de oportunidades de batching:**")
            st.code("""
-- 🔄 Análisis de batching inteligente
SELECT 
    p.id as pedido_existente,
    h3_distance(p.h3_destino, 'nuevo_destino_h3') as distancia_hexs,
    CASE 
        WHEN h3_distance(p.h3_destino, 'nuevo_destino_h3') = 0 THEN 15.0
        WHEN h3_distance(p.h3_destino, 'nuevo_destino_h3') = 1 THEN 10.0  
        WHEN h3_distance(p.h3_destino, 'nuevo_destino_h3') = 2 THEN 5.0
        ELSE 0.0
    END as ahorro_minutos
FROM pedidos p
WHERE p.rider_id = rider_id 
  AND p.status IN ('asignado', 'en_camino')
  AND h3_distance(p.h3_destino, 'nuevo_destino_h3') <= 2;
            """, language="sql")
            
            st.info("🔄 **Calcula automáticamente si vale la pena agrupar entregas por proximidad H3**")
        
        with tab3:
            st.markdown("**Routing multi-destino con PostGIS:**")
            st.code("""
-- 🛣️ Cálculo de ruta optimizada multi-parada
WITH waypoints AS (
    SELECT 1 as orden, rider_ubicacion as punto, 'rider' as tipo
    UNION ALL
    SELECT 2 as orden, entrega_existente as punto, 'entrega_1' as tipo  
    UNION ALL
    SELECT 3 as orden, tienda_coords as punto, 'pickup' as tipo
    UNION ALL
    SELECT 4 as orden, cliente_coords as punto, 'entrega_2' as tipo
)
SELECT 
    ST_MakeLine(punto ORDER BY orden) as ruta_completa,
    ST_Length(ruta_completa::geography) / 1000 as km_totales,
    (km_totales / 25.0 * 60) + 10 as minutos_estimados
FROM waypoints;
            """, language="sql")
            
            st.info("🛣️ **Una sola ruta para múltiples destinos - exactamente como optimiza Rappi!**")

def setup_inicial():
    """Setup inicial de riders demo"""
    if st.sidebar.button("🔧 Setup Riders Demo"):
        with st.spinner("Configurando riders..."):
            resultado = call_api("/api/debug/setup-riders", "GET")
            if resultado:
                st.sidebar.success(f"✅ {resultado.get('riders', 0)} riders configurados")
                st.rerun()
            else:
                st.sidebar.error("❌ Error en setup")

def simular_movimiento_rider():
    """Simular movimiento del rider por la ruta"""
    if not st.session_state.get('tracking_activo'):
        return
    
    # Auto-refresh cada 30 segundos para simular movimiento
    if st.session_state.get('auto_refresh', True):
        time.sleep(30)
        st.rerun()

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Aplicación principal"""
    
    # Inicializar session state
    if 'tracking_activo' not in st.session_state:
        st.session_state.tracking_activo = False
    if 'pedido_actual' not in st.session_state:
        st.session_state.pedido_actual = None
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    
    # Header principal
    st.markdown('<h1 class="main-header">🗺️ RutIA - Ruteo Inteligente con IA</h1>', unsafe_allow_html=True)
    st.markdown("**Tracking en tiempo real como Rappi, pero mostrando la magia espacial por detrás**")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Controles")
        setup_inicial()
        
        st.markdown("### 🔄 Auto-refresh")
        auto_refresh = st.checkbox("Tracking automático", value=True)
        st.session_state.auto_refresh = auto_refresh
        
        if st.button("🛑 Parar Tracking"):
            st.session_state.tracking_activo = False
            st.session_state.pedido_actual = None
            st.rerun()
    
    # Configuración empresa
    empresa_config = get_empresa_config()
    
    # Layout principal
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        # Tracking activo o simulador
        tracking_data = mostrar_tracking_activo()
        
        if not tracking_data:
            simular_pedido_whatsapp()
        
        # Obtener datos de riders
        riders_data = call_api("/api/riders") or []
        
        # Crear mapa
        mapa = crear_mapa_tracking(empresa_config, riders_data, tracking_data)
        
        # Mostrar mapa
        st.markdown("### 🗺️ Mapa de Tracking en Tiempo Real")
        mapa_data = st_folium(mapa, width=700, height=500)
        
        # Info adicional si hay tracking
        if tracking_data:
            rider = tracking_data.get('rider')
            if rider:
                st.markdown(f"""
                <div class="rider-card">
                    <h4>🛵 {rider['nombre']} está llevando tu pedido</h4>
                    <p>📍 Ubicación actual: H3 {rider['h3_actual']}</p>
                    <p>⚡ Score eficiencia: {rider['eficiencia_score']:.1f}/100</p>
                    {f"<p>🔄 <strong>Entrega agrupada para mayor eficiencia</strong></p>" if tracking_data.get('es_batch') else ""}
                </div>
                """, unsafe_allow_html=True)
    
    with col_side:
        # Métricas del sistema
        mostrar_metricas_sistema()
        
        # Estado de riders
        st.markdown("### 🛵 Riders Disponibles")
        if riders_data:
            for rider in riders_data[:4]:  # Mostrar max 4
                status_color = "🟢" if rider['pedidos_activos'] == 0 else "🟡"
                batch_indicator = " 🔄" if rider.get('tiene_pedido_cerca_local') else ""
                
                st.markdown(f"""
                {status_color} **{rider['nombre']}**{batch_indicator}  
                📍 H3: `{rider['h3_actual'][:8]}...`  
                📦 Pedidos: {rider['pedidos_activos']}/3
                """)
        else:
            st.info("🔧 Ejecutar setup de riders demo")
        
        # Empresa info
        st.markdown("### 🏪 Configuración")
        st.markdown(f"""
        **{empresa_config['nombre']}**  
        📍 {empresa_config['direccion']}  
        🔶 H3: `{h3.geo_to_h3(empresa_config['lat'], empresa_config['lon'], 9)[:8]}...`
        """)
    
    # Queries espaciales (parte inferior)
    mostrar_queries_espaciales()
    
    # Auto-refresh si está activo
    if st.session_state.auto_refresh and st.session_state.tracking_activo:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()