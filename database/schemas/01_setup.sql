-- =============================================================================
-- RutIA - Setup inicial base de datos
-- =============================================================================

-- Habilitar PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- TODO: Implementar schemas completos
-- - Tabla empresa
-- - Tabla riders
-- - Tabla pedidos  
-- - Tabla rutas_calculadas
-- - Índices espaciales H3
