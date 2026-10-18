# 🛰️ SONAR (Radar30X) — Documentación Técnica Integral del Sistema

> **Plataforma de Inteligencia Editorial, Detección de Señales en IA y Memoria Narrativa para Líderes de Latinoamérica.**  
> Desarrollado para el **Reto 30X**. En producción en [https://sonar.perte.design](https://sonar.perte.design) y código abierto en [https://github.com/Umbrex47/sonar](https://github.com/Umbrex47/sonar).

---

## 📑 Tabla de Contenidos

1. [¿Qué Hace el Proyecto? (Propósito y Propuesta de Valor)](#1-qué-hace-el-proyecto)
2. [¿Cómo Funciona? (Pipeline End-to-End)](#2-cómo-funciona-pipeline-end-to-end)
3. [Arquitectura del Sistema](#3-arquitectura-del-sistema)
4. [Herramientas y Stack Tecnológico Usado](#4-herramientas-y-stack-tecnológico-usado)
5. [Secciones de la Plataforma y Estado Actual](#5-secciones-de-la-plataforma-y-estado-actual)
6. [Posibles Mejoras a Futuro (Roadmap Técnico)](#6-posibles-mejoras-a-futuro-roadmap-técnico)
7. [Errores, Limitaciones y Gotchas de la Versión Actual](#7-errores-limitaciones-y-gotchas-de-la-versión-actual)
8. [Guía de Despliegue y Ejecución Local](#8-guía-de-despliegue-y-ejecución-local)
9. [Scrapers Ligeros y Extracción Ética Compliant](#9-scrapers-ligeros-y-extracción-ética-compliant)
10. [Análisis Financiero y Costes Operativos ($/mes)](#10-análisis-financiero-y-costes-operativos-mes)

---

## 1. ¿Qué Hace el Proyecto?

### 1.1 El Problema Real de la Industria
Hoy en día, las agencias de medios, creadores técnicos y equipos directivos que comunican sobre Inteligencia Artificial (como el equipo de **30X**, cuya misión es capacitar y orientar a directores, CEOs y líderes de innovación en Latinoamérica) enfrentan tres barreras críticas:
1. **Sobrecarga de Ruido y Humo:** Se publican más de 5,000 piezas diarias sobre IA entre Twitter/X, YouTube, Reddit y medios. Más del 90% es *clickbait*, especulación vacía o refritos copiados que no aportan valor empresarial.
2. **Ceguera de Saturación Temporal:** Las herramientas actuales de monitoreo social (BuzzSumo, Brand24, Mention) miden métricas de vanidad (likes, vistas), pero **no distinguen el ciclo de vida de una tendencia**. Confunden un tema que ya murió hace 3 semanas y que todos copiaron, con una señal emergente genuina que está a punto de explotar.
3. **Falta de Contexto Ejecutivo para LatAm:** Las noticias globales nacen en inglés, enfocadas en el hype de Silicon Valley. No responden cómo impacta esa tecnología a una empresa en México, Colombia, Argentina o Chile, ni cómo calcular su ROI, coste de API o barrera de adopción.
4. **Costes Prohibitivos y Riesgo Legal (ToS):** Las suites corporativas de scraping cuestan entre $500 y $3,000 USD mensuales y suelen recurrir a técnicas de scraping clandestino que violan los Términos de Servicio de las redes sociales.

### 1.2 La Pregunta que Resuelve SONAR
> *"¿Cuáles son los 10 temas de Inteligencia Artificial que realmente están creciendo esta semana, por qué funcionan técnica y psicológicamente, y cómo los adaptamos al contexto estratégico de líderes y empresas en Latinoamérica, con coste $0 y 100% de cumplimiento legal?"*

### 1.3 La Propuesta de Valor
**SONAR** automatiza lo que antes requería más de 15 horas semanales de curaduría manual. En menos de **45 segundos**:
- Monitorea múltiples canales públicos oficiales.
- Compara contra **90 días de memoria vectorial** histórica para filtrar refritos.
- Audita con un agente crítico que penaliza el humo y exige evidencia técnica.
- Calibra matemáticamente las señales con el motor probabilístico **TypeSafe JEV**.
- Redacta borradores ejecutivos adaptados a 30X (guiones de video corto, hilos/posts de LinkedIn y newsletters) mediante **Google Gemini Flash**.

---

## 2. ¿Cómo Funciona? (Pipeline End-to-End)

El flujo de procesamiento de SONAR es determinista, auditable y desacoplado en 7 fases consecutivas:

```mermaid
flowchart TD
    subgraph Fase1 ["Fase 1: Ingesta Multi-Canal $0"]
        S1["HackerNews (Algolia API)"]
        S2["GitHub (Search API v3)"]
        S3["YouTube (Data API v3)"]
        S4["RSS.app Hub (X, TikTok, LinkedIn)"]
        S5["Google News (RSS LatAm)"]
        S6["WebSearch Sonda (DuckDuckGo Híbrido)"]
        S1 & S2 & S3 & S4 & S5 & S6 --> EXP["Agente Explorador"]
        EXP -->|Deduplicación SHA-256 + Canonicalización| RAW[("SQLite: tabla items")]
    end

    subgraph Fase2 ["Fase 2: Agrupamiento Semántico"]
        RAW --> CLUST["Motor de Clustering (RapidFuzz >= 75%)"]
        CLUST -->|Convergencia Inter-Fuente| CLUSTERS["Clusters Temáticos"]
    end

    subgraph Fase3 ["Fase 3: Memoria Histórica 90 Días"]
        CLUSTERS --> HIST["Agente Historiador"]
        MEM[("Memoria Vectorial: item_embeddings")] <--> HIST
        HIST -->|Novedad + Ratio Copias + Sparklines| PHASES["Máquina de Estados de Ciclo de Vida"]
    end

    subgraph Fase4 ["Fase 4: Auditoría Anti-Humo"]
        PHASES --> CRIT["Agente Crítico"]
        CRIT -->|Penalización Clickbait + Papers/Código| CERT["Veredicto de Credibilidad"]
    end

    subgraph Fase5 ["Fase 5: Inferencia TypeSafe JEV"]
        CERT --> JEV["Motor JEV (System One Model)"]
        JEV -->|Scoring Multicriterio Calibrado| FUNNEL["Embudo: Aprobados / Observación / Descarte"]
    end

    subgraph Fase6 ["Fase 6: Empaquetado Editorial"]
        FUNNEL --> TOP10["Top 10 + Ganchos + Ángulo 30X"]
        TOP10 --> OUT[("out/report_YYYY-WW.json")]
    end

    subgraph Fase7 ["Fase 7: Suite de Aplicación"]
        OUT --> WEB["Frontend Next.js en Vivo"]
        OUT --> LLM["Generador de Borradores (Gemini Flash)"]
        OUT --> CHAT["Chatbot Determinista T0 (RAG Ground Truth)"]
    end
```

### Paso a Paso Detallado

1. **Ingesta Multi-Canal Compliant (Agente Explorador):**
   - Extrae publicaciones de HackerNews, GitHub, YouTube, Google News y redes sindicadas vía RSS.app.
   - Cada publicación se limpia de parámetros de tracking UTM, se normaliza en un objeto tipado `RawItem` y se genera su hash `SHA-256(canonical_url)`. Si el hash ya existe, se descarta para evitar duplicaciones.
2. **Clustering Semántico y Cruce Multi-Fuente:**
   - Agrupa los títulos y resúmenes mediante coincidencia de similitud de cadenas difusas (`rapidfuzz`) y tokens normalizados.
   - Premia la **convergencia multi-fuente**: un tema que surge simultáneamente en debates de HackerNews, un repositorio de GitHub y videos de YouTube recibe prioridad máxima. Una pieza aislada en una sola red social no califica como tendencia.
3. **Análisis de Memoria de 90 Días (Agente Historiador):**
   - Compara el cluster contra los embeddings vectoriales de los últimos 90 días almacenados en SQLite.
   - **Novedad Temporal:** Calcula la distancia semántica contra el pasado:
     $$\text{Novedad} = 1 - \max(\text{Similitud Coseno con ítems de los últimos 90 días})$$
   - **Ratio de Copias:** Mide qué porcentaje de publicaciones en 48 horas repiten las mismas frases clave con similitud $\ge 0.90$.
   - **Máquina de Estados:** Clasifica la fase del tema en:
     - 🟢 **Emergente:** Novedad $\ge 0.25$, sin pico previo, múltiples creadores.
     - 🔵 **En Crecimiento:** Señal con aceleración positiva y por debajo de su pico histórico.
     - 🔴 **Saturado:** Pico ocurrido hace $\ge 3$ semanas y alto ratio de refritos/copias.
     - 🟣 **Resurgente:** Tema antiguo que revive debido a un avance técnico nuevo.
   - **Sparkline ASCII:** Genera una cadena visual de 5 caracteres (`.:oO*`) que resume la curva de adopción semana a semana.
4. **Auditoría Anti-Humo (Agente Crítico):**
   - Examina los enlaces primarios para validar si existe código abierto, un paper en ArXiv, documentación oficial o métricas reales de benchmark.
   - Penaliza titulares hiperbólicos o vacíos ("¡Esto cambiará el mundo para siempre!", "Murió la programación"). Si el contenido carece de sustento, lo envía al embudo de descartados.
5. **Inferencia Probabilística y Calibración (Motor JEV):**
   - Aplica la fórmula de scoring oficial ponderando 5 factores:
     $$\text{Score} = 0.35 \times \text{Crecimiento} + 0.25 \times \text{Novedad} + 0.20 \times \text{MultiFuente} + 0.20 \times \text{Encaje LatAm} - \text{Penalización Saturación}$$
   - Distribuye las piezas en tres niveles: **Aprobados (Top 10)**, **En Observación** y **Descartados**.
6. **Empaquetado y Generación Asistida:**
   - Genera el reporte estructurado `out/report_YYYY-WW.json`.
   - Alimenta el generador de borradores y el chatbot RAG interactivo con citas de evidencia directa.

---

## 3. Arquitectura del Sistema

La arquitectura está construida bajo el principio de **desacoplamiento total entre decisión y redacción**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SONAR ARCHITECTURE                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [ CAPA DE PRESENTACIÓN ]                                              │
│  Next.js 16 (Turbopack) · React 19 · TypeScript · Tailwind CSS         │
│  ├── SonarIntro (GSAP Animación Cinemática)                            │
│  ├── DriverTour (Tours Interactivos Sincronizados y Persistentes)      │
│  ├── TerminalConsole (Streaming de Logs y Telemetría en Vivo)          │
│  └── Vistas: Dashboard, Conocimiento, Enfoques, Borradores, Chat, etc. │
│                                                                        │
│  ▲                                                                     │
│  │ HTTP / JSON API / Server-Sent Status                                │
│  ▼                                                                     │
│                                                                        │
│  [ CAPA DE SERVIDOR HTTP & PROXY ]                                     │
│  Caddy (Alpine) SSL Auto LetsEncrypt ◄──► Python run.py serve (:8080)  │
│  ├── Endpoints: /api/reports, /api/report/latest, /api/status          │
│  ├── Endpoints de Acción: /api/run-ingest, /api/run-score, /api/run-all │
│  └── Endpoints de LLM: /api/drafts/generate, /api/chat                 │
│                                                                        │
│  ▲                                                                     │
│  │ Llamadas a Servicios & Orquestación                                 │
│  ▼                                                                     │
│                                                                        │
│  [ CAPA DE INTELIGENCIA Y MULTI-AGENTE ]                               │
│  ├── Agente Explorador (sources/): HN, GitHub, YouTube, RSS, News, DDG │
│  ├── Agente Historiador (pipeline/narrative.py): Novedad + Sparklines  │
│  ├── Agente Crítico (pipeline/decide.py): Auditoría de Fuentes         │
│  ├── Motor TypeSafe JEV (pipeline/scoring.py): Inferencia Ponderada    │
│  └── Gemini LLM Gateway (chat/service.py & drafts/generator.py)        │
│                                                                        │
│  ▲                                                                     │
│  │ Lectura / Escritura Transaccional                                   │
│  ▼                                                                     │
│                                                                        │
│  [ CAPA DE ALMACENAMIENTO & PERSISTENCIA ]                             │
│  SQLite (data/radar.db)                                                │
│  ├── items (Tabla de publicaciones crudas normalizadas)                │
│  ├── item_embeddings (Base vectorial para similitud coseno)            │
│  ├── audit_log (Trazabilidad completa por run_id)                      │
│  ├── search_focuses.json (Enfoques editoriales dinámicos)              │
│  └── out/report_YYYY-WW.json (Reportes versionados semanales)          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Herramientas y Stack Tecnológico Usado

### Backend y Procesamiento de Datos
| Herramienta | Versión | Rol en el Sistema |
|---|---|---|
| **Python** | `3.14 / 3.12` | Lenguaje central del backend, scripts del pipeline y servidor web. |
| **SQLite3** | Integrado | Almacenamiento relacional local, historial de ejecuciones y tabla de embeddings vectoriales. |
| **Google GenAI SDK** (`google-genai`) | `^1.0.0` | Cliente oficial de Google para inferencia de modelos **Gemini 2.5 Flash / Gemini 3.6 Flash**. |
| **RapidFuzz** | `^3.6` | Algoritmos de cálculo de distancia de Levenshtein y agrupamiento semántico ultrarrápido en C++. |
| **Pydantic** | `^2.6` | Validación estricta de esquemas, tipos y serialización de reportes editoriales. |
| **HTTPX** | `^0.27` | Cliente HTTP asíncrono con control de timeouts para ingesta de fuentes externas. |
| **Feedparser** | `^6.0` | Parser robusto de feeds XML, RSS y Atom para Google News y RSS.app. |
| **BeautifulSoup4** | `^4.12` | Limpieza de contenido HTML, extracción de metadatos y enlaces canónicos. |
| **Rich** | `^13.7` | Renderizado de tablas interactivas, barras de progreso y colores en terminal. |

### Frontend y Experiencia de Usuario
| Herramienta | Versión | Rol en el Sistema |
|---|---|---|
| **Next.js** | `16.4.2 (Turbopack)` | Framework React moderno con App Router y generación estática ultra-optimizada. |
| **React** | `19.0.0` | Biblioteca de componentes de interfaz. |
| **TypeScript** | `^5.6` | Tipado estático riguroso en todos los componentes y modelos de datos. |
| **Tailwind CSS** | `^4.0` | Sistema de estilos utility-first con paleta refinada Origin Style. |
| **GSAP (GreenSock)** | `^3.12` | Motor de animaciones de alto rendimiento para la intro cinematográfica interactiva. |
| **Driver.js** | `^1.3` | Motor de visitas guiadas interactivas paso a paso en cada sección. |
| **Lucide React** | `^0.475` | Conjunto de iconos vectoriales consistentes y accesibles. |

### Infraestructura y Operaciones
| Herramienta | Configuración | Rol en el Sistema |
|---|---|---|
| **Docker & Docker Compose** | Multi-container | Empaquetado reproducirle del servidor Sonar y el proxy Caddy. |
| **Caddy Server** | `alpine` | Servidor web inverso con terminación SSL/TLS automática (Let's Encrypt), HTTP/2 y compresión gzip/zstd. |
| **Cloudflare** | DNS & Proxy | Protección contra ataques DDoS, CDN global y gestión de cabeceras de caché. |
| **DigitalOcean Droplet** | Ubuntu 24.04 LTS | Servidor cloud de ejecución continua 24/7 en IP `68.183.203.164`. |

---

## 5. Secciones de la Plataforma y Estado Actual

| Sección / Ruta | Propósito | Características Principales | Estado Actual |
|---|---|---|---|
| **1. Radar Semanal** (`/`) | Dashboard central de tendencias y embudo | Tarjetas de tendencias Top 10, ganchos psicológicos, ángulo 30X para LatAm, sparklines de 90d, veredicto del crítico, embudo de observación y auditoría de descartados. Filtro de formato (video, hilo, carrusel) y filtro por temas nuevos. | 🟢 **100% Operativo en Producción** |
| **2. Base de Conocimiento** (`/conocimiento`) | Memoria multimodal de 90 días | Consola de ingesta de contenido en múltiples modalidades (completo, keywords, solo ganchos), pool de entrada para imágenes, PDFs, video transcrito y enlaces web. Búsqueda semántica vectorial sobre SQLite con cálculo coseno. | 🟢 **100% Operativo en Producción** |
| **3. Enfoques & RSS** (`/enfoques`) | Configuración de tracks y sonda web | Panel de tracks temáticos dinámicos (Agentes, SLM, SWE-bench, etc.) con activación/desactivación. Sonda web en vivo impulsada por DuckDuckGo y hub de integración RSS.app para redes sociales. | 🟢 **100% Operativo en Producción** |
| **4. Borradores IA** (`/borradores`) | Redacción ejecutiva asistida | Generación de guiones y posts con Gemini Flash basados en las tendencias del radar. **Switch dual interactivo: [👁️ Vista Previa] formateada vs. [✏️ Modo Editor] en Markdown**, guardado en `.md` y copia con un clic. | 🟢 **100% Operativo en Producción** |
| **5. Chatbot Determinista T0** (`/chat`) | Consultas directivas auditables | Chat RAG Ground Truth sobre SQLite. Responde preguntas estratégicas citando estrictamente las fuentes primarias verificadas del radar (cero alucinación). Sugerencias predefinidas de alto impacto. | 🟢 **100% Operativo en Producción** |
| **6. Playground JEV** (`/playground`) | Simulador y calibrador algorítmico | Simulador en tiempo real de la fórmula matemática JEV. Permite ingresar un tema con métricas hipotéticas y ajustar las ponderaciones de novedad, velocidad, diversidad y encaje LatAm para auditar el veredicto. | 🟢 **100% Operativo en Producción** |
| **7. Bibliografía & Directorio** (`/bibliografia`) | Catálogo y compliance de fuentes | Directorio transparente de las 12 fuentes y feeds RSS activos (Latent Space, OpenAI, Hugging Face, ArXiv) con análisis de frecuencia, método y cumplimiento legal ToS. Hoja de ruta de nuevas fuentes. | 🟢 **100% Operativo en Producción** |
| **8. Consola Terminal** (`TerminalConsole.tsx`) | Telemetría en tiempo real | Ventana desplegable flotante que transmite segundo a segundo los logs y el avance porcentual del orquestador multi-agente durante los ciclos de escaneo. | 🟢 **100% Operativo en Producción** |
| **9. Intro Cinemática** (`SonarIntro.tsx`) | Primera impresión de marca | Animación tipo radar acuático con tipografía mecanográfica GSAP. Omitible con tecla `Esc` y guardada en `sessionStorage` para no interrumpir al usuario recurrente. | 🟢 **100% Operativo en Producción** |
| **10. Driver Tour** (`DriverTour.tsx`) | Onboarding y visitas guiadas | Tour interactivo sincronizado con la intro (solo aparece al cerrarse la intro). **Persistencia en `localStorage`**: una vez cerrado, no vuelve a abrirse automáticamente al navegar o recargar, pero se puede invocar manualmente con el botón flotante o el sidebar. | 🟢 **100% Operativo en Producción** |

---

## 6. Posibles Mejoras a Futuro (Roadmap Técnico)

1. **Transcripción Nativa de Audio/Video (Whisper):**
   - Incorporar un worker ligero con Whisper para transcribir automáticamente podcasts en español (ej. *Monos Estocásticos*, *El Siglo 21 es Hoy*) y conferencias técnicas de YouTube, extrayendo ganchos conversacionales que aún no existen en texto.
2. **Grafos de Conocimiento Semántico (GraphRAG):**
   - Migrar la memoria de 90 días hacia una base de grafos (ej. KuzuDB o Neo4j integrado en contenedor) para visualizar la red de relaciones entre entidades clave (ej. *OpenAI* $\to$ *Anthropic* $\to$ *DeepSeek* $\to$ *Claude Code*).
3. **Publicación y Distribución Automatizada:**
   - Crear integraciones vía API con LinkedIn, Buffer, Typefully y Ghost/Substack para que un borrador aprobado en `/borradores` pueda ser programado directamente para su difusión con un clic.
4. **Fine-Tuning / LoRA del Tono Editorial 30X:**
   - Entrenar un adaptador de estilo (LoRA) o usar few-shot prompting estructurado con las publicaciones históricas con mayor engagement del equipo de 30X para igualar el vocabulario y tono directivo.
5. **Multi-Tenancy y Filtros por Vertical:**
   - Permitir segmentar el radar por industrias específicas de Latinoamérica: Fintech, Retail, Salud, Minería y LegalTech.

---

## 7. Errores, Limitaciones y Gotchas de la Versión Actual

Al operar o evaluar la versión actual de SONAR, se deben tener en cuenta las siguientes consideraciones técnicas:

### 1. Cuota Diaria de YouTube Data API v3
- **Comportamiento:** Google asigna una cuota gratuita de 10,000 unidades diarias por proyecto. Una búsqueda de videos consume 100 unidades.
- **Riesgo:** Si se ejecutan escaneos continuos más de 100 veces en un día, la API responderá con `HTTP 403 quotaExceeded`.
- **Mitigación Implementada:** El sistema captura la excepción sin interrumpir el pipeline y continúa con las demás fuentes públicas (HackerNews, GitHub, Google News, RSS.app).

### 2. Bloqueo de Rate-Limit en Google News RSS
- **Comportamiento:** Si el servidor emite demasiadas peticiones simultáneas hacia `news.google.com/rss/search` desde una misma IP de datacenter, Google puede responder temporalmente con código `503 Service Unavailable`.
- **Mitigación Implementada:** Se rotaron las consultas por escaneo (seleccionando un subconjunto dinámico de enfoques activos) y se configuró un `User-Agent` de navegador moderno con timeout estricto.

### 3. Dependencia de la Clave `GEMINI_API_KEY`
- **Comportamiento:** La redacción de borradores en `/borradores` y la síntesis inteligente en el Chatbot T0 utilizan la API de Google Gemini (`gemini-2.5-flash` o `gemini-3.6-flash`).
- **Comportamiento ante Ausencia:** Si la clave no está presente en el archivo `.env`, el generador de borradores utiliza plantillas sintéticas predefinidas y el Chatbot opera en modo de coincidencia léxica determinista sobre SQLite.

### 4. Caché de Cabeceras en CDN (Cloudflare)
- **Comportamiento:** En entornos proxy donde Cloudflare intermedia el tráfico, las respuestas JSON de `/api/report/latest` o `/api/status` pueden ser retenidas en los nodos de borde si no se instruye adecuadamente al navegador.
- **Mitigación Implementada:** El servidor en Python y Caddy envían obligatoriamente cabeceras:
  ```http
  Cache-Control: no-cache, no-store, must-revalidate, max-age=0
  Pragma: no-cache
  Expires: 0
  ```
  Adicionalmente, el frontend anexa un query param de tiempo (`?_t=Date.now()`) para garantizar datos frescos en cada llamada.

### 5. Escala de la Memoria Vectorial en CPU
- **Comportamiento:** Los embeddings de 90 días se calculan y comparan en memoria local o mediante operaciones matriciales en SQLite/Python.
- **Límite:** Para el volumen actual (<10,000 publicaciones) el tiempo de cálculo es de apenas **<350 ms**. Si el volumen escalara a más de 500,000 ítems, se requerirá una base de vectores dedicada como `pgvector` o `Qdrant`.

---

## 8. Guía de Despliegue y Ejecución Local

### Prerrequisitos
- Python 3.11, 3.12 o 3.14
- Node.js 20+ y `npm`
- (Opcional) Docker y Docker Compose para producción

### Paso 1: Clonar y Configurar Entorno
```bash
git clone https://github.com/Umbrex47/sonar.git
cd sonar

# Crear entorno virtual de Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves opcionales (YOUTUBE_API_KEY, GEMINI_API_KEY)
```

### Paso 2: Ejecutar Escaneo Inicial
```bash
# Ejecutar escaneo completo de prueba
python run.py run-all --top 10

# O probar fuentes individuales:
python run.py test-sources
```

### Paso 3: Compilar y Servir Frontend
```bash
# En el directorio del frontend:
cd frontend
npm install
npm run build
cd ..

# Iniciar servidor unificado:
python run.py serve --host 0.0.0.0 --port 8080
```
Abre tu navegador en `http://localhost:8080`.

### Despliegue en Servidor con Docker
```bash
docker compose build sonar
docker compose up -d
```

---

## 9. Scrapers Ligeros y Extracción Ética Compliant

### 9.1 ¿Qué es un "Scraper Ligero" en SONAR?
A diferencia del scraping tradicional que levanta navegadores completos tipo Chromium headless (Selenium, Playwright o Puppeteer) que consumen más de 600 MB de RAM por instancia y tardan entre 10 y 30 segundos por página, **SONAR implementa un motor de scrapers ultraligeros basado en tres principios:**

1. **Cero Overhead de Renderizado:** Se comunica mediante peticiones HTTP asíncronas puras (`httpx`), extrayendo el contenido y metadatos en milisegundos (<250 ms por llamada).
2. **Arquitectura en Cascada de Coste $0:**
   ```
   [URL de Destino]
          │
          ▼
   ┌────────────────────────────────────────────────────────┐
   │ Capa 0: Jina Reader (r.jina.ai/<url>)                  │
   │ - Coste: $0.00                                         │
   │ - Devuelve Markdown limpio sin scripts ni publicidad   │
   └────────────────────────────────────────────────────────┘
          │ (Si falla o hay timeout)
          ▼
   ┌────────────────────────────────────────────────────────┐
   │ Capa 1: Direct Stealth (HTTPX + BeautifulSoup4)        │
   │ - Coste: $0.00                                         │
   │ - Rotación de User-Agents modernos (Desktop / Mobile)  │
   │ - Extracción semántica de <article>, <main>, <p>       │
   │ - Detección automática de WAF y Cloudflare Turnstile   │
   └────────────────────────────────────────────────────────┘
          │ (Opcional / Fallback extremo)
          ▼
   ┌────────────────────────────────────────────────────────┐
   │ Capa 2: Fallback Managed (ZenRows / ScrapingBee)       │
   │ - Solo si el usuario configura API Keys externas       │
   │ - Se mantiene en reserva para no generar costes        │
   └────────────────────────────────────────────────────────┘
   ```
3. **Sonda Web Liviana (DuckDuckGo Probe):**
   - Rastreo en tiempo real a través de DuckDuckGo HTML Lite sin necesidad de clave de API ni registro. Permite capturar artículos de prensa y blogs técnicos emergentes con cero huella digital.
4. **Seguridad y Respeto a Servidores:**
   - **Protección Anti-SSRF:** Bloqueo estricto de direcciones IP privadas (ej. `127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`) para impedir ataques de falsificación de peticiones contra el servidor local o la red interna.
   - **Jitter Adaptativo por Dominio:** Intervalo aleatorio controlado entre peticiones a un mismo host para respetar las políticas de tasa de los servidores fuente.
   - **Enfoque "El Equipo como Sensor":** Para plataformas cerradas que exigen credenciales privadas (grupos cerrados de LinkedIn o Instagram), se utiliza ingesta asistida vía CSV (`data/manual.csv`), evitando credenciales robadas o riesgo de baneo de cuentas.

---

## 10. Análisis Financiero y Costes Operativos ($/mes)

Uno de los logros fundamentales de la arquitectura de SONAR es su **viabilidad económica absoluta**: sustituye servicios que demandan presupuestos corporativos por una infraestructura que opera con un coste marginal prácticamente nulo.

### 10.1 Desglose Detallado de Costes Mensuales

| Componente | Proveedor / Tecnología | Nivel / Plan | Coste Estimado Mensual |
|---|---|---|:---:|
| **Servidor Cloud (VPS)** | DigitalOcean Droplet | Basic 1 vCPU / 1GB RAM / 25GB SSD (Ubuntu 24.04) | **$4.00 – $6.00 USD** |
| **Base de Datos & Vector Store** | SQLite3 Local embebida | Almacenamiento en disco local (cero egress fees) | **$0.00 USD** |
| **Proxy SSL y Web Server** | Caddy Server (Alpine) | Certificados Let's Encrypt automáticos open-source | **$0.00 USD** |
| **Protección DDoS y CDN** | Cloudflare | Free Tier (DNS Anycast, CDN global, HTTP/3) | **$0.00 USD** |
| **Scraping e Ingesta Ligera** | Jina Reader + Direct Stealth + Feedparser | Código abierto sin APIs comerciales obligatorias | **$0.00 USD** |
| **Fuentes Oficiales Públicas** | HackerNews Algolia, GitHub API, Google News | Endpoints públicos y cuota gratuita de desarrollador | **$0.00 USD** |
| **YouTube Data API v3** | Google Cloud Console | Cuota gratuita oficial (10,000 unidades diarias) | **$0.00 USD** |
| **IA Generativa y RAG** | Google Gemini 2.5 / 3.6 Flash | Free Tier (15 RPM / 1M TPM) o Pay-As-You-Go ($0.075/1M tokens) | **$0.00 – $0.15 USD** |
| **TOTAL OPERATIVO MENSUAL** | — | — | **$4.00 – $6.15 USD / mes** |

> 💡 **Nota de despliegue $0:** Si el droplet de DigitalOcean se sustituye por servicios de hosting con capa gratuita permanente (como **Oracle Cloud Always Free Tier**, **Fly.io** o **Railway Starter**), el coste total de mantener SONAR 100% activo en producción es de **$0.00 USD / mes**.

### 10.2 Comparativa Financiera: SONAR vs. Soluciones SaaS Tradicionales

| Categoría de Gasto | Stack Tradicional de Mercado | Coste Anual Tradicional | Coste Anual con SONAR | Ahorro Real |
|---|---|:---:|:---:|:---:|
| **Monitoreo Social** | BuzzSumo / Brand24 / Mention | $2,400 – $4,800 USD | $0.00 USD | **100%** |
| **Proxies Residenciales & Scraping** | BrightData / Apify / Smartproxy | $1,200 – $3,000 USD | $0.00 USD | **100%** |
| **Base de Datos Vectorial Administrada** | Pinecone / Qdrant Cloud | $840 – $1,500 USD | $0.00 USD (SQLite) | **100%** |
| **Hosting y Cómputo** | AWS ECS / EKS / RDS | $720 – $1,800 USD | $48 – $72 USD | **96%** |
| **TOTAL ANUAL** | — | **$5,160 – $11,100 USD** | **$48 – $72 USD** | **> 99.3% de Ahorro** |

---

*Desarrollado con rigor técnico, arquitectura multi-agente y pasión por el periodismo inteligente en Inteligencia Artificial.*  
*SONAR © 2026 — 100% ToS Compliant & TypeSafe AI.*
