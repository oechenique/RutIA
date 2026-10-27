# RutIA — resumen en español

[🇬🇧 English](README.md)

Pedís una hamburguesa y, detrás, se despierta un pequeño motor espacial. RutIA es un demo de delivery que muestra el trabajo geoespacial que esconde una app como Rappi o Glovo: geocoding, hexágonos H3, calles de OpenStreetMap, ruteo en PostGIS y un rider que se mueve punto por punto en un mapa.

- **Cómo funciona**: el formulario del menú dispara un flujo de n8n, que llama a la API (FastAPI). La API guarda el pedido en PostGIS, asigna un rider con anillos H3 alrededor del local y dispara un DAG de Airflow de 11 tareas: geocoding con Nominatim, análisis H3, extracción de calles por Overpass, guardado en PostGIS, ruteo y tracking.
- **El demo en vivo está apagado**: corría en Docker local expuesto con ngrok durante un webinar de GeoDojo (agosto de 2025). El menú y la página de tracking cargan, pero sin backend.
- **Límites**: pgRouting no está verificado (la imagen de PostGIS no lo trae y el setup no crea la extensión; la API cae a una ruta recta), hay dos `docker-compose` y las credenciales por defecto son solo para el demo local: se cambian en `.env` antes de desplegar.
- **Cómo lo haría hoy**: infraestructura como código y un gestor de secretos, capas separadas (tipo Medallion) en vez de una sola base compartida con Airflow, CI con tests de las funciones espaciales y un contrato de datos para el JSON del pedido.

Para levantarlo: `cp .env.example .env`, cambiar cada `change-me` y `docker compose up -d`.
