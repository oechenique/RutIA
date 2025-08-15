-- =============================================================================
-- RutIA - Schema Principal de Base de Datos
-- Tablas optimizadas para análisis espacial con H3 y PostGIS
-- =============================================================================

-- Configuración inicial
SET timezone = 'America/Argentina/Buenos_Aires';

-- =============================================================================
-- TIPOS ENUM PERSONALIZADOS
-- =============================================================================

CREATE TYPE rider_status AS ENUM (
    'disponible',
    'ocupado', 
    'offline',
    'pausado'
);

CREATE TYPE pedido_status AS ENUM (
    'pendiente',
    'asignado',
    'recogiendo',
    'en_camino',
    'entregado',
    'cancelado'
);

CREATE TYPE zona_tipo AS ENUM (
    'residencial',
    'comercial',
    'industrial',
    'mixta',
    'universitaria'
);

-- =============================================================================
-- TABLA 1: EMPRESA - Configuración central del sistema
-- =============================================================================

CREATE TABLE IF NOT EXISTS empresa (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT NOT NULL,
    
    -- 🗺️ UBICACIÓN ESPACIAL
    coordenadas GEOMETRY(POINT, 4326) NOT NULL,
    h3_location TEXT NOT NULL,
    h3_resolution INTEGER DEFAULT 9,
    
    -- 🔶 ÁREA DE COBERTURA H3
    h3_area_cobertura TEXT[] NOT NULL DEFAULT '{}',
    radio_cobertura_hexs INTEGER DEFAULT 5,
    
    -- ⚙️ CONFIGURACIÓN OPERATIVA
    activo BOOLEAN DEFAULT TRUE,
    horario_apertura TIME DEFAULT '08:00',
    horario_cierre TIME DEFAULT '23:00',
    
    -- 📊 MÉTRICAS
    pedidos_procesados INTEGER DEFAULT 0,
    tiempo_promedio_entrega REAL DEFAULT 25.0,
    
    -- 🕐 TIMESTAMPS
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices espaciales empresa
CREATE INDEX IF NOT EXISTS idx_empresa_coordenadas ON empresa USING GIST(coordenadas);
CREATE INDEX IF NOT EXISTS idx_empresa_h3_location ON empresa USING BTREE(h3_location);
CREATE INDEX IF NOT EXISTS idx_empresa_h3_cobertura ON empresa USING GIN(h3_area_cobertura);

-- =============================================================================
-- TABLA 2: RIDERS - Actores móviles del sistema
-- =============================================================================

CREATE TABLE IF NOT EXISTS riders (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    telefono TEXT UNIQUE,
    email TEXT,
    
    -- 🗺️ UBICACIÓN ESPACIAL EN TIEMPO REAL
    ubicacion_actual GEOMETRY(POINT, 4326) NOT NULL,
    h3_actual TEXT NOT NULL,
    h3_cobertura TEXT[] NOT NULL DEFAULT '{}',
    
    -- 🎯 ESTADO OPERATIVO
    status rider_status DEFAULT 'disponible',
    pedidos_activos INTEGER DEFAULT 0,
    capacidad_maxima INTEGER DEFAULT 3,
    
    -- 🔄 BATCHING INTELLIGENCE
    tiene_pedido_cerca_local BOOLEAN DEFAULT FALSE,
    destino_pedido_existente GEOMETRY(POINT, 4326),
    h3_destino_existente TEXT,
    
    -- 📊 MÉTRICAS DE PERFORMANCE
    entregas_completadas INTEGER DEFAULT 0,
    rating_promedio REAL DEFAULT 5.0,
    tiempo_promedio_entrega REAL DEFAULT 25.0,
    km_recorridos_total REAL DEFAULT 0.0,
    eficiencia_score REAL DEFAULT 50.0,
    
    -- ⚙️ CONFIGURACIÓN
    velocidad_promedio_kmh REAL DEFAULT 25.0,
    radio_cobertura_hexs INTEGER DEFAULT 3,
    activo BOOLEAN DEFAULT TRUE,
    
    -- 🕐 TIMESTAMPS Y TRACKING
    ultima_ubicacion_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ultimo_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices espaciales riders (CRÍTICOS para performance)
CREATE INDEX IF NOT EXISTS idx_riders_ubicacion_actual ON riders USING GIST(ubicacion_actual);
CREATE INDEX IF NOT EXISTS idx_riders_h3_actual ON riders USING BTREE(h3_actual);
CREATE INDEX IF NOT EXISTS idx_riders_h3_cobertura ON riders USING GIN(h3_cobertura);
CREATE INDEX IF NOT EXISTS idx_riders_status ON riders USING BTREE(status);
CREATE INDEX IF NOT EXISTS idx_riders_disponibles ON riders USING BTREE(status, pedidos_activos) 
    WHERE status = 'disponible';

-- Índice compuesto para búsquedas optimizadas
CREATE INDEX IF NOT EXISTS idx_riders_busqueda_optima ON riders 
    USING BTREE(status, pedidos_activos, eficiencia_score DESC)
    WHERE status = 'disponible' AND pedidos_activos < capacidad_maxima;

-- =============================================================================
-- TABLA 3: PEDIDOS - Eventos espaciales del sistema
-- =============================================================================

CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    pedido_externo_id TEXT UNIQUE, -- Para integración con n8n
    
    -- 👤 INFORMACIÓN CLIENTE
    cliente_nombre TEXT,
    cliente_telefono TEXT,
    cliente_direccion TEXT NOT NULL,
    
    -- 🗺️ UBICACIÓN ESPACIAL DESTINO
    coordenadas_entrega GEOMETRY(POINT, 4326) NOT NULL,
    h3_destino TEXT NOT NULL,
    
    -- 📦 CONTENIDO Y DETALLES
    items JSONB NOT NULL DEFAULT '{}', -- {"hamburguesa_gis": 1, "coca": 1}
    descripcion_items TEXT,
    peso_estimado_kg REAL DEFAULT 1.0,
    precio_total DECIMAL(10,2) DEFAULT 0.00,
    
    -- 🛵 ASIGNACIÓN RIDER
    rider_id INTEGER REFERENCES riders(id),
    empresa_id INTEGER REFERENCES empresa(id) DEFAULT 1,
    
    -- 🔄 BATCHING Y OPTIMIZACIÓN
    es_batch BOOLEAN DEFAULT FALSE,
    pedido_principal_id INTEGER REFERENCES pedidos(id),
    orden_en_ruta INTEGER DEFAULT 1, -- 1=primero, 2=segundo, etc.
    batch_group_id TEXT, -- UUID para agrupar batches
    
    -- 📍 ESTADO Y PROGRESO
    status pedido_status DEFAULT 'pendiente',
    
    -- ⏰ TIEMPOS CRÍTICOS
    timestamp_pedido TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    timestamp_asignado TIMESTAMP WITH TIME ZONE,
    timestamp_recogido TIMESTAMP WITH TIME ZONE,
    timestamp_en_camino TIMESTAMP WITH TIME ZONE,
    timestamp_entregado TIMESTAMP WITH TIME ZONE,
    timestamp_cancelado TIMESTAMP WITH TIME ZONE,
    
    -- 🎯 ESTIMACIONES Y MÉTRICAS
    tiempo_estimado_minutos INTEGER,
    tiempo_real_minutos INTEGER,
    distancia_estimada_km REAL,
    distancia_real_km REAL,
    
    -- 🛣️ INFORMACIÓN DE RUTA (cache)
    ruta_calculada_id INTEGER, -- FK a rutas_calculadas
    waypoints_ruta GEOMETRY(MULTIPOINT, 4326),
    
    -- 📊 CALIDAD Y FEEDBACK
    satisfaccion_cliente INTEGER CHECK (satisfaccion_cliente BETWEEN 1 AND 5),
    comentarios_cliente TEXT,
    comentarios_rider TEXT,
    
    -- 🕐 TIMESTAMPS
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices espaciales pedidos
CREATE INDEX IF NOT EXISTS idx_pedidos_coordenadas_entrega ON pedidos USING GIST(coordenadas_entrega);
CREATE INDEX IF NOT EXISTS idx_pedidos_h3_destino ON pedidos USING BTREE(h3_destino);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos USING BTREE(status);
CREATE INDEX IF NOT EXISTS idx_pedidos_rider_id ON pedidos USING BTREE(rider_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_timestamp ON pedidos USING BTREE(timestamp_pedido DESC);

-- Índices para queries de batching
CREATE INDEX IF NOT EXISTS idx_pedidos_batching ON pedidos 
    USING BTREE(rider_id, status, h3_destino)
    WHERE status IN ('asignado', 'en_camino');

-- Índice para análisis temporal
CREATE INDEX IF NOT EXISTS idx_pedidos_analisis_temporal ON pedidos 
    USING BTREE(DATE(timestamp_pedido), h3_destino, status);

-- =============================================================================
-- TABLA 4: RUTAS_CALCULADAS - Cache inteligente de rutas PostGIS
-- =============================================================================

CREATE TABLE IF NOT EXISTS rutas_calculadas (
    id SERIAL PRIMARY KEY,
    
    -- 🎯 IDENTIFICACIÓN DE RUTA
    ruta_hash TEXT UNIQUE NOT NULL, -- Hash MD5 de origen+destino+waypoints
    rider_id INTEGER REFERENCES riders(id),
    pedido_id INTEGER REFERENCES pedidos(id),
    
    -- 🗺️ GEOMETRÍA DE RUTA COMPLETA
    geometria_ruta GEOMETRY(LINESTRING, 4326) NOT NULL,
    waypoints GEOMETRY(MULTIPOINT, 4326),
    waypoints_h3 TEXT[] DEFAULT '{}',
    
    -- 📊 MÉTRICAS CALCULADAS
    distancia_total_km REAL NOT NULL,
    tiempo_estimado_minutos INTEGER NOT NULL,
    tiempo_real_minutos INTEGER,
    
    -- 🔄 INFORMACIÓN DE BATCHING
    incluye_batch BOOLEAN DEFAULT FALSE,
    numero_paradas INTEGER DEFAULT 1,
    orden_paradas JSONB DEFAULT '[]', -- ["origen", "parada1", "destino"]
    secuencia_h3 TEXT[] DEFAULT '{}',
    
    -- ⚡ OPTIMIZACIÓN Y PERFORMANCE
    algoritmo_usado TEXT DEFAULT 'postgis_dijkstra',
    calidad_ruta REAL DEFAULT 1.0, -- 0.0-1.0 score
    trafico_considerado BOOLEAN DEFAULT FALSE,
    factor_trafico REAL DEFAULT 1.0,
    
    -- 🕐 VALIDEZ Y CACHE
    veces_utilizada INTEGER DEFAULT 0,
    ultima_utilizacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
    
    -- 🌐 METADATOS OSM
    osm_data_version TEXT,
    osm_elements_count INTEGER DEFAULT 0,
    
    -- 🕐 TIMESTAMPS
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para rutas calculadas
CREATE INDEX IF NOT EXISTS idx_rutas_geometria ON rutas_calculadas USING GIST(geometria_ruta);
CREATE INDEX IF NOT EXISTS idx_rutas_waypoints ON rutas_calculadas USING GIST(waypoints);
CREATE INDEX IF NOT EXISTS idx_rutas_hash ON rutas_calculadas USING BTREE(ruta_hash);
CREATE INDEX IF NOT EXISTS idx_rutas_rider_pedido ON rutas_calculadas USING BTREE(rider_id, pedido_id);
CREATE INDEX IF NOT EXISTS idx_rutas_expires ON rutas_calculadas USING BTREE(expires_at)
    WHERE expires_at > NOW();

-- Índice para cache lookup optimizado
CREATE INDEX IF NOT EXISTS idx_rutas_cache_lookup ON rutas_calculadas 
    USING BTREE(ruta_hash, expires_at DESC)
    WHERE expires_at > NOW();

-- =============================================================================
-- FUNCIONES DE BASE DE DATOS PERSONALIZADAS
-- =============================================================================

-- Función para calcular distancia H3 (fallback si no hay extensión H3)
CREATE OR REPLACE FUNCTION h3_distance_fallback(h3_origin TEXT, h3_dest TEXT)
RETURNS INTEGER AS $$
DECLARE
    origin_coords GEOMETRY;
    dest_coords GEOMETRY;
    distance_km REAL;
BEGIN
    -- Convertir H3 a coordenadas (aproximación)
    -- En producción usar extensión H3 real
    origin_coords := ST_Point(
        CAST(SUBSTRING(h3_origin FROM 5 FOR 8) AS INTEGER) / 1000000.0 - 180,
        CAST(SUBSTRING(h3_origin FROM 13 FOR 8) AS INTEGER) / 1000000.0 - 90
    );
    
    dest_coords := ST_Point(
        CAST(SUBSTRING(h3_dest FROM 5 FOR 8) AS INTEGER) / 1000000.0 - 180,
        CAST(SUBSTRING(h3_dest FROM 13 FOR 8) AS INTEGER) / 1000000.0 - 90
    );
    
    -- Calcular distancia aproximada en km
    distance_km := ST_Distance(origin_coords::geography, dest_coords::geography) / 1000.0;
    
    -- Convertir a "distancia en hexágonos" (aproximación)
    RETURN GREATEST(1, ROUND(distance_km / 0.5)::INTEGER);
EXCEPTION
    WHEN OTHERS THEN
        RETURN 999; -- Fallback si algo falla
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Función para actualizar timestamp de update automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para auto-update de timestamps
CREATE TRIGGER update_empresa_updated_at BEFORE UPDATE ON empresa
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_riders_updated_at BEFORE UPDATE ON riders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pedidos_updated_at BEFORE UPDATE ON pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rutas_updated_at BEFORE UPDATE ON rutas_calculadas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- DATOS INICIALES (SEED DATA)
-- =============================================================================

-- Insertar empresa por defecto (se sobrescribe con datos del .env)
INSERT INTO empresa (
    nombre, 
    direccion, 
    coordenadas, 
    h3_location,
    h3_area_cobertura
) VALUES (
    'RutIA Demo',
    'Blanco Encalada 2680, CABA',
    ST_Point(-58.3816, -34.6037),
    '881f1a4a2ffffff', -- H3 aproximado para demo
    ARRAY['881f1a4a2ffffff', '881f1a4a3ffffff', '881f1a4a7ffffff']
) ON CONFLICT DO NOTHING;

-- =============================================================================
-- VISTAS ÚTILES PARA ANÁLISIS
-- =============================================================================

-- Vista de riders disponibles con información espacial
CREATE OR REPLACE VIEW riders_disponibles AS
SELECT 
    r.id,
    r.nombre,
    r.telefono,
    r.h3_actual,
    ST_Y(r.ubicacion_actual) as lat,
    ST_X(r.ubicacion_actual) as lon,
    r.pedidos_activos,
    r.capacidad_maxima,
    r.tiene_pedido_cerca_local,
    r.eficiencia_score,
    r.rating_promedio,
    array_length(r.h3_cobertura, 1) as hexagons_cobertura
FROM riders r
WHERE r.status = 'disponible' 
  AND r.activo = TRUE
  AND r.pedidos_activos < r.capacidad_maxima;

-- Vista de pedidos activos con información completa
CREATE OR REPLACE VIEW pedidos_activos AS
SELECT 
    p.id,
    p.cliente_nombre,
    p.cliente_telefono,
    p.h3_destino,
    ST_Y(p.coordenadas_entrega) as destino_lat,
    ST_X(p.coordenadas_entrega) as destino_lon,
    p.status,
    p.rider_id,
    r.nombre as rider_nombre,
    r.h3_actual as rider_h3,
    p.tiempo_estimado_minutos,
    p.es_batch,
    p.timestamp_pedido,
    EXTRACT(EPOCH FROM (NOW() - p.timestamp_pedido))/60 as minutos_transcurridos
FROM pedidos p
LEFT JOIN riders r ON p.rider_id = r.id
WHERE p.status IN ('pendiente', 'asignado', 'recogiendo', 'en_camino');

-- Vista de métricas en tiempo real
CREATE OR REPLACE VIEW metricas_tiempo_real AS
SELECT 
    -- Contadores básicos
    (SELECT COUNT(*) FROM riders WHERE status = 'disponible') as riders_disponibles,
    (SELECT COUNT(*) FROM pedidos WHERE status IN ('pendiente', 'asignado', 'en_camino')) as pedidos_activos,
    (SELECT COUNT(*) FROM pedidos WHERE status = 'entregado' AND DATE(timestamp_entregado) = CURRENT_DATE) as entregas_hoy,
    
    -- Métricas de eficiencia
    (SELECT AVG(tiempo_real_minutos) FROM pedidos WHERE status = 'entregado' AND timestamp_entregado >= NOW() - INTERVAL '24 hours') as tiempo_promedio_24h,
    (SELECT COUNT(*) * 100.0 / NULLIF(COUNT(*), 0) FROM pedidos WHERE es_batch = TRUE AND timestamp_pedido >= CURRENT_DATE) as porcentaje_batching_hoy,
    
    -- Hexágonos más demandados
    (SELECT h3_destino FROM pedidos WHERE timestamp_pedido >= CURRENT_DATE GROUP BY h3_destino ORDER BY COUNT(*) DESC LIMIT 1) as h3_mas_demandado,
    
    -- Timestamp de actualización
    NOW() as actualizado_en;

-- =============================================================================
-- PERMISOS Y COMENTARIOS
-- =============================================================================

-- Comentarios en las tablas principales
COMMENT ON TABLE empresa IS 'Configuración central del sistema RutIA';
COMMENT ON TABLE riders IS 'Riders/delivery persons con ubicación e inteligencia espacial H3';
COMMENT ON TABLE pedidos IS 'Pedidos con análisis espacial, batching y tracking completo';
COMMENT ON TABLE rutas_calculadas IS 'Cache de rutas PostGIS con optimización multi-destino';

-- Comentarios en columnas clave
COMMENT ON COLUMN riders.h3_cobertura IS 'Array de hexágonos H3 que puede cubrir el rider';
COMMENT ON COLUMN riders.tiene_pedido_cerca_local IS 'Flag para optimización de batching automático';
COMMENT ON COLUMN pedidos.h3_destino IS 'Hexágono H3 del destino para análisis espacial optimizado';
COMMENT ON COLUMN rutas_calculadas.ruta_hash IS 'Hash MD5 para cache lookup ultra-rápido';

-- Crear usuario de aplicación (opcional, para producción)
-- CREATE USER rutia_app WITH PASSWORD 'rutia_app_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rutia_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rutia_app;

-- =============================================================================
-- VALIDACIONES Y CONSTRAINTS ADICIONALES
-- =============================================================================

-- Validar que H3 tenga formato correcto (15 caracteres hexadecimales)
ALTER TABLE empresa ADD CONSTRAINT check_h3_format 
    CHECK (h3_location ~ '^[0-9a-f]{15}$');

ALTER TABLE riders ADD CONSTRAINT check_rider_h3_format 
    CHECK (h3_actual ~ '^[0-9a-f]{15}$');

ALTER TABLE pedidos ADD CONSTRAINT check_pedido_h3_format 
    CHECK (h3_destino ~ '^[0-9a-f]{15}$');

-- Validar que coordenadas estén en rango válido
ALTER TABLE empresa ADD CONSTRAINT check_coordenadas_validas
    CHECK (ST_X(coordenadas) BETWEEN -180 AND 180 AND ST_Y(coordenadas) BETWEEN -90 AND 90);

ALTER TABLE riders ADD CONSTRAINT check_rider_coordenadas_validas
    CHECK (ST_X(ubicacion_actual) BETWEEN -180 AND 180 AND ST_Y(ubicacion_actual) BETWEEN -90 AND 90);

-- Validar que timestamps estén en orden lógico
ALTER TABLE pedidos ADD CONSTRAINT check_timestamps_orden
    CHECK (
        timestamp_asignado IS NULL OR timestamp_asignado >= timestamp_pedido AND
        timestamp_recogido IS NULL OR timestamp_recogido >= timestamp_asignado AND
        timestamp_en_camino IS NULL OR timestamp_en_camino >= timestamp_recogido AND
        timestamp_entregado IS NULL OR timestamp_entregado >= timestamp_en_camino
    );

-- =============================================================================
-- FINALIZACIÓN
-- =============================================================================

-- Actualizar estadísticas para el optimizador de queries
ANALYZE empresa;
ANALYZE riders;
ANALYZE pedidos;
ANALYZE rutas_calculadas;

-- Log de creación exitosa
DO $$
BEGIN
    RAISE NOTICE '🗺️ RutIA Database Schema creado exitosamente';
    RAISE NOTICE '📊 Tablas: empresa, riders, pedidos, rutas_calculadas';
    RAISE NOTICE '🚀 Índices espaciales H3 configurados';
    RAISE NOTICE '⚡ Vistas de análisis disponibles';
    RAISE NOTICE '✅ Sistema listo para procesamiento espacial inteligente';
END $$;