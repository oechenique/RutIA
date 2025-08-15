# RutIA - Guía de Instalación Windows

## Prerrequisitos
- Docker Desktop for Windows
- 4GB RAM mínimo  
- Puertos 3000, 8080, 8501 disponibles

## Quick Start
```cmd
# 1. Ejecutar setup
setup_rutia.cmd

# 2. Configurar empresa
cd rutia
notepad .env

# 3. Levantar sistema
docker-compose up -d

# 4. Verificar
start http://localhost:8501
start http://localhost:3000
start http://localhost:8080
```

## Configuración .env
Cambiar coordenadas según tu ubicación:
```env
EMPRESA_LAT=-34.6037    # Tu latitud
EMPRESA_LON=-58.3816    # Tu longitud  
EMPRESA_DIRECCION=Tu dirección completa
```
