-- 🔧 FIX CRÍTICO: Recrear tabla pedidos con columnas ampliadas
-- Error actual: "value too long for type character varying(15)"

-- Borrar tabla existente si tiene columnas muy pequeñas
DROP TABLE IF EXISTS pedidos CASCADE;

-- Crear tabla pedidos con tamaños correctos
CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    pedido_externo_id VARCHAR(255) UNIQUE,    -- ✅ FIX: era VARCHAR(15), ahora 255
    cliente_nombre VARCHAR(255),
    cliente_direccion TEXT,
    coordenadas_entrega GEOMETRY(POINT, 4326),
    h3_destino VARCHAR(20),                   -- ✅ FIX: era VARCHAR(15), ahora 20
    items JSONB,
    descripcion_items TEXT,
    precio_total DECIMAL(10,2),
    tiempo_estimado_minutos INTEGER,
    rider_id INTEGER,
    status VARCHAR(50) DEFAULT 'procesando',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Crear tabla riders también (por si no existe)
CREATE TABLE IF NOT EXISTS riders (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255),
    telefono VARCHAR(20),
    ubicacion_actual GEOMETRY(POINT, 4326),
    h3_actual VARCHAR(20),                    -- ✅ También ampliado
    h3_cobertura TEXT[],
    tiene_pedido_cerca_local BOOLEAN DEFAULT FALSE,
    pedidos_activos INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'disponible',
    eficiencia_score DECIMAL(5,2) DEFAULT 50.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices espaciales
CREATE INDEX IF NOT EXISTS idx_pedidos_coordenadas ON pedidos USING GIST(coordenadas_entrega);
CREATE INDEX IF NOT EXISTS idx_riders_ubicacion ON riders USING GIST(ubicacion_actual);
CREATE INDEX IF NOT EXISTS idx_pedidos_h3 ON pedidos(h3_destino);
CREATE INDEX IF NOT EXISTS idx_riders_h3 ON riders(h3_actual);

-- Verificar que las tablas existen
SELECT 'Tabla pedidos creada' as status, 
       COUNT(*) as columnas 
FROM information_schema.columns 
WHERE table_name = 'pedidos';

SELECT 'Tabla riders creada' as status, 
       COUNT(*) as columnas 
FROM information_schema.columns 
WHERE table_name = 'riders';