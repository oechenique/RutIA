# 🚀 RutIA: Delivery con Routing Real

**Sistema de delivery que muestra toda la complejidad espacial oculta** de apps como Uber, Rappi y Glovo.  
Usa las mismas tecnologías que usan ellos: **H3, PostGIS, pgRouting y OpenStreetMap**.

## 🎯 Demo en Vivo

**1. Hacer un pedido** → https://oechenique.github.io/la-geografica-menu/  
**2. Ver el tracking** → https://la-geografica-tracking.vercel.app/

Vas a ver cómo se extraen 16+ calles reales, se calcula la ruta óptima y se mueve el rider punto por punto.

## 🔥 Lo que hace por dentro

```
Cliente: "Pedí una hamburguesa"

RutIA ejecuta:
🌍 Geocoding real con OpenStreetMap
🔶 Sistema hexagonal H3 (como Uber)
🗺️ Extracción masiva de calles via OSM
🛢️ Base de datos espacial PostGIS
🧮 Routing Dijkstra REAL con pgRouting
📡 Tracking vectorial matemático
```

## 🏗️ Arquitectura

```
[Cliente] → [n8n] → [PostgreSQL+PostGIS] → [pgRouting] → [Tracking Web]
              ↓            ↓                    ↓            ↓
           Pedidos    Calles OSM         Ruta óptima    Leaflet.js
```

## ⚙️ Instalación Local

```bash
# 1. Clonar
git clone https://github.com/oechenique/rutia.git
cd rutia

# 2. Levantar servicios
docker-compose up -d

# 3. Exponer con ngrok
ngrok http 3000
```

Configurar el webhook de ngrok en n8n.cloud y listo.

## 💻 Stack Técnico

- **Backend:** PostgreSQL + PostGIS + pgRouting + FastAPI
- **Spatial:** H3 Hexagonal System + OpenStreetMap + Overpass API  
- **Frontend:** Leaflet.js + Vercel
- **Orchestration:** Apache Airflow + n8n

## 🎯 Por qué importa

**Sin estas tecnologías NO EXISTE Uber, Rappi, Airbnb.**  
RutIA revela toda la complejidad que normalmente está oculta.

## Let's Connect! 一緒に学びましょう 🌐

[![Twitter Badge](https://img.shields.io/badge/-@GastonEchenique-1DA1F2?style=flat&logo=x&logoColor=white&link=https://x.com/GastonEchenique)](https://x.com/GastonEchenique)
[![LinkedIn Badge](https://img.shields.io/badge/-Gastón_Echenique-0A66C2?style=flat&logo=Linkedin&logoColor=white&link=https://www.linkedin.com/in/gaston-echenique/)](https://www.linkedin.com/in/gaston-echenique/)
[![GitHub Badge](https://img.shields.io/badge/-oechenique-333?style=flat&logo=github&logoColor=white&link=https://github.com/oechenique)](https://github.com/oechenique)
[![GeoAnalytics Badge](https://img.shields.io/badge/-GeoAnalytics_Site-2ecc71?style=flat&logo=google-earth&logoColor=white&link=https://oechenique.github.io/geoanalytics/)](https://oechenique.github.io/geoanalytics/)
[![Discord Badge](https://img.shields.io/badge/-Gastón|ガストン-5865F2?style=flat&logo=discord&logoColor=white&link=https://discord.com/users/gastonechenique)](https://discord.com/users/gastonechenique)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/rhrqmdyaig)

---

**Construido por el arquitecto de soluciones geoespaciales más crack de Argentina** 🇦🇷
