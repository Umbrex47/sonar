"""Servidor HTTP nativo y ligero para la interfaz web de Radar30X.

No requiere frameworks pesados adicionales; utiliza la librería estándar de Python
(http.server.ThreadingHTTPServer) para responder con latencia ultrabaja (< 5ms)
y servir la API de reportes, enriquecimiento de evidencias y ejecución en segundo plano.
"""

from datetime import datetime, timezone
import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv

load_dotenv()

from pipeline.db import Database

logger = logging.getLogger("radar30x.web")

# Estado global de ejecución del pipeline y streaming de logs
RUN_STATE: Dict[str, Any] = {
    "is_running": False,
    "last_run": None,
    "last_status": "idle",  # "idle" | "running" | "success" | "error" | "cancelled"
    "last_error": None,
    "command_label": "Ninguna",
    "command": "",
    "started_at": None,
    "finished_at": None,
    "duration_seconds": 0.0,
    "current_step": "Listo",
    "progress_percent": 0,
    "logs": [],
}
RUN_LOCK = threading.Lock()
CURRENT_PROCESS: Optional[subprocess.Popen] = None


def get_base_dir() -> Path:
    """Retorna el directorio raíz del proyecto radar30x."""
    return Path(__file__).resolve().parent.parent


def get_db_path() -> str:
    """Retorna la ruta a la base de datos SQLite."""
    if "RADAR_DB_PATH" in os.environ:
        return os.environ["RADAR_DB_PATH"]
    return str(get_base_dir() / "data" / "radar.db")


def get_out_dir() -> Path:
    """Retorna el directorio de reportes out/."""
    return get_base_dir() / "out"


def enrich_report_references(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquece las URLs de evidencia con datos detallados (título, fuente, autor, métricas) desde SQLite,
    tanto para top_temas como para temas_en_observacion."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return report_data

    # Mapear URLs a datos del ítem e indexar por título/tema para matching de observación
    items_by_url: Dict[str, Dict[str, Any]] = {}
    items_by_title: Dict[str, Dict[str, Any]] = {}
    items_by_canonical: Dict[str, List[Dict[str, Any]]] = {}
    all_items: List[Dict[str, Any]] = []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT fuente, titulo, url, autor, fecha, metricas_json, tema_canonico FROM items")
        for row in cur.fetchall():
            url = row["url"]
            try:
                metricas = json.loads(row["metricas_json"] or "{}")
            except Exception:
                metricas = {}
            item_info = {
                "fuente": row["fuente"],
                "titulo": row["titulo"],
                "autor": row["autor"] or "Redacción / Autor",
                "fecha": row["fecha"] or "",
                "metricas": metricas,
                "url": url,
            }
            items_by_url[url] = item_info
            norm_title = (row["titulo"] or "").lower().strip()
            if norm_title:
                items_by_title[norm_title] = item_info
            norm_can = (row["tema_canonico"] or "").lower().strip()
            if norm_can:
                items_by_canonical.setdefault(norm_can, []).append(item_info)
            all_items.append(item_info)
        conn.close()
    except Exception as e:
        logger.warning("No se pudo conectar a SQLite para enriquecer evidencias: %s", e)
        return report_data

    def _resolve_evidence(url: str) -> Dict[str, Any]:
        if url in items_by_url:
            return items_by_url[url]
        domain = urlparse(url).netloc.replace("www.", "") or "Fuente externa"
        path_slug = urlparse(url).path.strip("/").split("/")[-1].replace("-", " ").title()
        titulo_fb = path_slug if path_slug else domain
        return {
            "fuente": domain.split(".")[0].capitalize(),
            "titulo": titulo_fb,
            "autor": domain,
            "fecha": "Reciente",
            "metricas": {},
            "url": url,
        }

    # Clonar reporte para enriquecer
    enriched = dict(report_data)

    # 1. Enriquecer top_temas
    top_temas = enriched.get("top_temas", [])
    new_top = []
    for t in top_temas:
        tema_copy = dict(t)
        raw_evidencia = tema_copy.get("evidencia", [])
        referencias_detalladas = [_resolve_evidence(u) for u in raw_evidencia]
        tema_copy["referencias_detalladas"] = referencias_detalladas
        new_top.append(tema_copy)
    enriched["top_temas"] = new_top

    # 2. Enriquecer temas_en_observacion
    temas_obs = enriched.get("temas_en_observacion", [])
    new_obs = []
    for obs in temas_obs:
        obs_copy = dict(obs)
        raw_evidencia = obs_copy.get("evidencia", [])

        if raw_evidencia:
            refs = [_resolve_evidence(u) for u in raw_evidencia]
        else:
            tema_txt = obs_copy.get("tema", "").lower().strip()
            matched_items: List[Dict[str, Any]] = []

            if tema_txt in items_by_title:
                matched_items.append(items_by_title[tema_txt])
            elif tema_txt in items_by_canonical:
                matched_items.extend(items_by_canonical[tema_txt][:3])

            if not matched_items:
                words = [w for w in tema_txt.split() if len(w) > 4]
                if words:
                    for it in all_items:
                        it_title = it["titulo"].lower()
                        if any(w in it_title for w in words[:3]):
                            matched_items.append(it)
                            if len(matched_items) >= 3:
                                break

            refs = matched_items[:3]
            raw_evidencia = [r["url"] for r in refs]

        obs_copy["evidencia"] = raw_evidencia
        obs_copy["referencias_detalladas"] = refs
        new_obs.append(obs_copy)

    enriched["temas_en_observacion"] = new_obs
    return enriched


def get_report_files() -> List[str]:
    """Retorna los archivos de reporte ordenados por semana (YYYY-WXX) descendente, priorizando reportes reales."""
    out_dir = get_out_dir()
    all_files = glob.glob(str(out_dir / "report_*.json"))
    real_files = [f for f in all_files if not f.endswith("report_sample.json")]
    target_list = real_files if real_files else all_files

    def _sort_key(file_path: str):
        match = re.search(r"(\d{4})-W(\d{1,2})", os.path.basename(file_path))
        if match:
            year, week = int(match.group(1)), int(match.group(2))
            return (year, week, os.path.getmtime(file_path))
        return (0, 0, os.path.getmtime(file_path))

    return sorted(target_list, key=_sort_key, reverse=True)


def load_latest_report() -> Optional[Dict[str, Any]]:
    """Carga el reporte JSON más reciente del directorio out/."""
    report_files = get_report_files()
    if not report_files:
        return None

    try:
        with open(report_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        return enrich_report_references(data)
    except Exception as e:
        logger.error("Error al cargar reporte más reciente: %s", e)
        return None


def load_report_by_name(filename: str) -> Optional[Dict[str, Any]]:
    """Carga un reporte específico por nombre de archivo."""
    # Sanitizar nombre de archivo
    safe_name = os.path.basename(filename)
    report_path = get_out_dir() / safe_name
    if not report_path.exists():
        return None

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return enrich_report_references(data)
    except Exception as e:
        logger.error("Error al cargar reporte %s: %s", filename, e)
        return None


def list_available_reports() -> List[Dict[str, str]]:
    """Lista todos los reportes disponibles en out/."""
    files = get_report_files()
    result = []
    for f in files:
        name = os.path.basename(f)
        semana = name.replace("report_", "").replace(".json", "")
        result.append({
            "filename": name,
            "semana": semana,
            "modified": datetime.fromtimestamp(os.path.getmtime(f), timezone.utc).isoformat(),
        })
    return result


def query_db_items(fuente: Optional[str] = None, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Consulta ítems almacenados en SQLite con filtros."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return []

    items = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = "SELECT fuente, titulo, resumen, url, autor, fecha, metricas_json FROM items WHERE 1=1"
        params: List[Any] = []

        if fuente and fuente.lower() != "todas":
            query += " AND LOWER(fuente) = ?"
            params.append(fuente.lower())

        if search:
            query += " AND (LOWER(titulo) LIKE ? OR LOWER(resumen) LIKE ?)"
            term = f"%{search.lower()}%"
            params.extend([term, term])

        query += " ORDER BY fecha DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        for row in cur.fetchall():
            try:
                metricas = json.loads(row["metricas_json"] or "{}")
            except Exception:
                metricas = {}
            items.append({
                "fuente": row["fuente"],
                "titulo": row["titulo"],
                "resumen": row["resumen"],
                "url": row["url"],
                "autor": row["autor"] or "Desconocido",
                "fecha": row["fecha"],
                "metricas": metricas,
            })
        conn.close()
    except Exception as e:
        logger.error("Error al consultar ítems en SQLite: %s", e)
    return items


def get_bibliography_data() -> Dict[str, Any]:
    """Retorna el catálogo estructurado de fuentes activas con conteos de SQLite y fuentes sugeridas."""
    db_path = get_db_path()
    fuentes_counts: Dict[str, int] = {}
    total_db_items = 0

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT fuente, count(*) FROM items GROUP BY fuente")
            for row in cur.fetchall():
                fuentes_counts[row[0]] = row[1]
                total_db_items += row[1]
            conn.close()
        except Exception as e:
            logger.warning("No se pudieron leer estadísticas de fuentes para bibliografía: %s", e)

    active_sources = [
        {
            "id": "youtube",
            "name": "YouTube Data API v3",
            "categoria": "Video & Formatos",
            "tipo": "API Oficial / RSS",
            "cadencia": "Cada 12 horas",
            "descripcion": "Monitoreo de tracción visual, velocidad de vistas por hora (VPH), duración y discriminación de formatos (shorts vs long-form).",
            "canales_destacados": ["DotCSV", "Carlos Alarcón AI", "Lex Fridman", "Fireship", "Matt Wolfe", "Y Combinator"],
            "url_oficial": "https://developers.google.com/youtube/v3",
            "estado": "Activo",
            "compliance": "100% compliant con términos de YouTube API",
            "total_items": fuentes_counts.get("YouTube", 0),
        },
        {
            "id": "googlenews",
            "name": "Google News RSS en Español",
            "categoria": "Prensa Internacional & LatAm",
            "tipo": "Feed RSS Público",
            "cadencia": "Cada 6 horas",
            "descripcion": "Cobertura periodística en tiempo real en México, Colombia, Chile, Argentina y España sobre IA, negocios y regulación.",
            "canales_destacados": ["El Economista", "Infobae", "El País", "TechCrunch en Español", "Forbes LatAm"],
            "url_oficial": "https://news.google.com",
            "estado": "Activo",
            "compliance": "100% público mediante RSS sin scraping de endpoints privados",
            "total_items": fuentes_counts.get("GoogleNews", 0),
        },
        {
            "id": "websearch",
            "name": "DuckDuckGo & Motores de Búsqueda Web",
            "categoria": "Búsqueda Web Automática",
            "tipo": "Search Engine API / HTML",
            "cadencia": "Cada 12 horas",
            "descripcion": "Ejecución continua de consultas cruzadas basadas en los enfoques activos de búsqueda de Radar30X.",
            "canales_destacados": ["DuckDuckGo HTML", "Tavily AI (opcional)", "Serper (opcional)"],
            "url_oficial": "https://duckduckgo.com",
            "estado": "Activo",
            "compliance": "Consultas públicas sin almacenamiento de datos personales",
            "total_items": fuentes_counts.get("WebSearch", 0),
        },
        {
            "id": "hackernews",
            "name": "Hacker News (Y Combinator)",
            "categoria": "Comunidad & Desarrolladores",
            "tipo": "Firebase REST API Oficial",
            "cadencia": "Cada 4 horas",
            "descripcion": "Detección temprana de proyectos de código abierto, Show HN, benchmarks y debates técnicos rigurosos con alta puntuación.",
            "canales_destacados": ["Show HN", "Ask HN", "Top Stories (+100 puntos)"],
            "url_oficial": "https://news.ycombinator.com",
            "estado": "Activo",
            "compliance": "API pública oficial sin límites agresivos",
            "total_items": fuentes_counts.get("HackerNews", 0),
        },
        {
            "id": "huggingface",
            "name": "Hugging Face Hub & Paper Trends",
            "categoria": "Modelos Open Source & Research",
            "tipo": "Hugging Face API",
            "cadencia": "Cada 12 horas",
            "descripcion": "Seguimiento de modelos SLM (DeepSeek, Qwen, Phi, Mistral), benchmarks de razonamiento y datasets en tendencia.",
            "canales_destacados": ["Trending Models", "Trending Papers", "Daily Papers"],
            "url_oficial": "https://huggingface.co",
            "estado": "Activo",
            "compliance": "API pública oficial de Hugging Face",
            "total_items": fuentes_counts.get("HuggingFace", 0),
        },
        {
            "id": "newsletters",
            "name": "Newsletters & Feeds RSS Especializados en IA",
            "categoria": "Curaduría & Análisis Ejecutivo",
            "tipo": "Substack, Atom & RSS Públicos (12 Feeds Activos)",
            "cadencia": "Cada 6-12 horas",
            "descripcion": "Monitoreo permanente de 12 canales sindicados de primer nivel: análisis de labs, benchmarks, arquitectura de agentes, ingeniería de LLMs y ecosistema de inversión.",
            "canales_destacados": [
                "Latent Space (swyx)", "Interconnects (Nathan Lambert)", "Import AI (Jack Clark)",
                "Simon Willison", "OpenAI News", "Hugging Face Blog", "The Rundown AI",
                "ArXiv cs.AI", "Startups LatAm", "Rest of World", "TechCrunch AI", "MIT Tech Review"
            ],
            "url_oficial": "https://www.latent.space",
            "estado": "Activo",
            "compliance": "100% público mediante sindicación RSS/Atom sin paywalls ni restricciones",
            "total_items": sum(fuentes_counts.get(k, 0) for k in [
                "The Rundown AI", "Startups LatAm", "Rest of World", "TechCrunch AI",
                "Latent Space", "Interconnects", "Import AI", "Simon Willison",
                "OpenAI News", "Hugging Face Blog", "ArXiv cs.AI", "MIT Tech Review",
                "Newsletters"
            ]),
        },
        {
            "id": "rssapp",
            "name": "RSS.app Custom Social Feeds",
            "categoria": "Redes Sociales & Viralidad",
            "tipo": "RSS Multi-Plataforma",
            "cadencia": "En demanda / Programada",
            "descripcion": "Monitoreo de señales virales en TikTok, X (Twitter), LinkedIn y Reddit sin credenciales propietarias.",
            "canales_destacados": ["TikTok IA Viral", "LinkedIn AI Influencers", "X AI Researchers"],
            "url_oficial": "https://rss.app",
            "estado": "Activo",
            "compliance": "Sindicación legal mediante proxy RSS.app",
            "total_items": fuentes_counts.get("TikTok (Captura)", 0) + fuentes_counts.get("LinkedIn (Captura)", 0),
        },
        {
            "id": "medium",
            "name": "Medium Engineering & AI Publications",
            "categoria": "Artículos Técnicos & Casos de Uso",
            "tipo": "Medium RSS Feeds",
            "cadencia": "Cada 12 horas",
            "descripcion": "Tutoriales de implementación, arquitecturas de agentes, reducción de costos en nube y casos de éxito en empresas.",
            "canales_destacados": ["Towards Data Science", "Better Programming", "Level Up Coding"],
            "url_oficial": "https://medium.com",
            "estado": "Activo",
            "compliance": "Feeds RSS públicos de Medium",
            "total_items": fuentes_counts.get("Medium", 0),
        },
        {
            "id": "github",
            "name": "GitHub Trending & Releases",
            "categoria": "Código & Repositorios",
            "tipo": "GitHub API / RSS",
            "cadencia": "Diario",
            "descripcion": "Repositorios de IA en explosión de estrellas, frameworks de agentes (LangGraph, CrewAI, AutoGen) y herramientas CLI.",
            "canales_destacados": ["github.com/trending/python", "github.com/trending/typescript"],
            "url_oficial": "https://github.com",
            "estado": "Activo",
            "compliance": "GitHub Public API",
            "total_items": fuentes_counts.get("GitHub", 0),
        },
        {
            "id": "reddit",
            "name": "Reddit AI Communities",
            "categoria": "Comunidad & Feedback Crítico",
            "tipo": "Reddit JSON/RSS Público",
            "cadencia": "Cada 6 horas",
            "descripcion": "Debates reales sobre desempeño de modelos, pruebas de estrés en hardware modesto y descontento con APIs cerradas.",
            "canales_destacados": ["r/LocalLLaMA", "r/MachineLearning", "r/ArtificialIntelligence"],
            "url_oficial": "https://reddit.com",
            "estado": "Activo",
            "compliance": "Endpoints públicos .json",
            "total_items": fuentes_counts.get("Reddit", 0),
        },
        {
            "id": "manual",
            "name": "Ingesta Manual & Señales de Campo",
            "categoria": "Datos Propios / Analistas",
            "tipo": "CSV Local (data/manual.csv)",
            "cadencia": "En demanda",
            "descripcion": "Canal para que analistas y directores inyecten notas de reuniones privadas, conferencias o descubrimientos propios.",
            "canales_destacados": ["Radar30X Internal Analysts"],
            "url_oficial": "file:///data/manual.csv",
            "estado": "Activo",
            "compliance": "Datos internos de la organización",
            "total_items": fuentes_counts.get("Manual", 0) + fuentes_counts.get("Instagram (Captura)", 0),
        },
    ]

    suggested_sources = [
        {
            "id": "arxiv_semantic",
            "name": "Semantic Scholar & ArXiv API Grafos de Citas",
            "categoria": "Pre-prints Científicos & Grafos",
            "impacto": "Muy Alto (Anticipación 3-6 meses)",
            "beneficio": "Mapeo automatizado del grafo de citas académicas de papers fundacionales sobre razonamiento (test-time compute, reasoning distillation) y nuevos algoritmos de atención.",
            "dificultad": "Baja (API pública gratuita sin clave obligatoria)",
            "url": "https://www.semanticscholar.org/product/api",
        },
        {
            "id": "substack_deep",
            "name": "Substack Deep Dive: SemiAnalysis & The Pragmatic Engineer",
            "categoria": "Newsletters & Ensayos Profundos",
            "impacto": "Alto (Pensamiento Estratégico)",
            "beneficio": "Análisis profundo sobre economía de cómputo en semiconductores (Dylan Patel / SemiAnalysis) y gestión de talento técnico en escala (Gergely Orosz).",
            "dificultad": "Baja (Feeds RSS XML abiertos)",
            "url": "https://substack.com",
        },
        {
            "id": "product_hunt",
            "name": "Product Hunt API v2",
            "categoria": "Lanzamientos de Producto (Día 0)",
            "impacto": "Medio-Alto (Oportunidades de Negocio)",
            "beneficio": "Registra herramientas y startups de IA en el momento exacto en que se presentan al mercado, capturando upvotes y tracción temprana.",
            "dificultad": "Media (Requiere Developer Token GraphQL)",
            "url": "https://api.producthunt.com/v2/docs",
        },
        {
            "id": "podcast_transcripts",
            "name": "Transcriptor Automático de Podcasts (Whisper AI)",
            "categoria": "Audio & Podcasts Ejecutivos",
            "impacto": "Alto (Declaraciones Exclusivas)",
            "beneficio": "Extrae declaraciones en crudo de podcasts clave (Dwarkesh Patel, Lex Fridman, No Priors, All-In) antes de que los medios las editen.",
            "dificultad": "Media (Descarga de audio MP3 + transcripción Whisper local)",
            "url": "https://github.com/openai/whisper",
        },
        {
            "id": "discord_telegram",
            "name": "Comunidades Discord / Telegram de Modelos Open Source",
            "categoria": "Comunidad Técnica en Tiempo Real",
            "impacto": "Alto (Detección de Fallos y Leaks)",
            "beneficio": "Canales de EleutherAI, Nous Research, vLLM y LangChain para enterarse de bugs, nuevos pesos y cambios en licencias en tiempo real.",
            "dificultad": "Alta (Requiere Bots dedicados o webhooks)",
            "url": "https://discord.com",
        },
        {
            "id": "sec_patents",
            "name": "Patentes USPTO & Filings Financieros SEC EDGAR",
            "categoria": "Propiedad Intelectual & Finanzas",
            "impacto": "Alto (Señales de Inversión y Capex)",
            "beneficio": "Reportes 10-Q y 10-K para auditar el gasto real en chips (NVIDIA/AMD) y patentes de agentes registradas por Big Tech.",
            "dificultad": "Media (APIs públicas de la SEC y Google Patents)",
            "url": "https://www.sec.gov/edgar/searchedgar/companysearch",
        },
    ]

    return {
        "resumen": {
            "total_fuentes_activas": len(active_sources),
            "total_items_indexados": total_db_items,
            "categorias_cubiertas": list(set(s["categoria"] for s in active_sources)),
            "fuentes_sugeridas_expansion": len(suggested_sources),
        },
        "active_sources": active_sources,
        "suggested_sources": suggested_sources,
    }


def cancel_current_run() -> bool:
    """Cancela el proceso que actualmente se esté ejecutando en terminal."""
    global CURRENT_PROCESS, RUN_STATE
    with RUN_LOCK:
        if not RUN_STATE["is_running"] or not CURRENT_PROCESS:
            return False
        try:
            CURRENT_PROCESS.terminate()
            RUN_STATE["is_running"] = False
            RUN_STATE["last_status"] = "cancelled"
            RUN_STATE["current_step"] = "Proceso cancelado por el usuario"
            RUN_STATE["logs"].append({
                "id": len(RUN_STATE["logs"]) + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": "🛑 Ejecución cancelada por el usuario desde la interfaz.",
                "level": "warning",
            })
            CURRENT_PROCESS = None
            return True
        except Exception as e:
            logger.warning("Error cancelando proceso: %s", e)
            return False


def start_process_run(subcommand_args: List[str], label: str = "Actualización Sonar") -> bool:
    """Ejecuta un subcomando de run.py en segundo plano y transmite stdout línea a línea."""
    global RUN_STATE, CURRENT_PROCESS

    with RUN_LOCK:
        if RUN_STATE["is_running"]:
            return False
        now_iso = datetime.now(timezone.utc).isoformat()
        RUN_STATE["is_running"] = True
        RUN_STATE["last_status"] = "running"
        RUN_STATE["last_error"] = None
        RUN_STATE["command_label"] = label
        RUN_STATE["command"] = f"python run.py {' '.join(subcommand_args)}"
        RUN_STATE["started_at"] = now_iso
        RUN_STATE["finished_at"] = None
        RUN_STATE["duration_seconds"] = 0.0
        RUN_STATE["current_step"] = f"Iniciando {label}..."
        RUN_STATE["progress_percent"] = 5
        RUN_STATE["logs"] = [
            {
                "id": 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": f"🚀 [{label}] Ejecutando: python run.py {' '.join(subcommand_args)}",
                "level": "step",
            }
        ]

    def worker():
        global RUN_STATE, CURRENT_PROCESS
        start_time = time.time()
        log_id = 1
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        python_bin = sys.executable
        run_script = str(get_base_dir() / "run.py")
        cmd = [python_bin, run_script] + subcommand_args

        try:
            logger.info("Iniciando subproceso con streaming de logs: %s", cmd)
            proc = subprocess.Popen(
                cmd,
                cwd=str(get_base_dir()),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            with RUN_LOCK:
                CURRENT_PROCESS = proc

            if proc.stdout:
                for raw_line in iter(proc.stdout.readline, ""):
                    if not raw_line and proc.poll() is not None:
                        break
                    line = raw_line.rstrip("\r\n")
                    if not line:
                        continue

                    log_id += 1
                    now_str = datetime.now().strftime("%H:%M:%S")

                    # Categorización semántica de logs para el frontend
                    level = "info"
                    lower_line = line.lower()
                    if "error" in lower_line or "exception" in lower_line or "traceback" in lower_line:
                        level = "error"
                    elif "warning" in lower_line or "⚠️" in line:
                        level = "warning"
                    elif "✅" in line or "✨" in line or "💾" in line:
                        level = "success"
                    elif any(k in line for k in ["[1/3]", "[2/3]", "[3/3]", "🔍", "🧠", "✍️", "🚀"]):
                        level = "step"

                    with RUN_LOCK:
                        # Detección de fases dinámicas
                        if "[1/3]" in line or "Iniciando Ingesta" in line:
                            RUN_STATE["current_step"] = "Fase 1/3: Ingesta de Fuentes Públicas"
                            RUN_STATE["progress_percent"] = 25
                        elif "Conectando con" in line:
                            src_name = line.split("Conectando con")[-1].strip().replace("...", "")
                            RUN_STATE["current_step"] = f"Ingestando: {src_name}"
                            RUN_STATE["progress_percent"] = max(RUN_STATE["progress_percent"], 35)
                        elif "[2/3]" in line or "Procesando Clustering" in line:
                            RUN_STATE["current_step"] = "Fase 2/3: Clustering Semántico y Decisiones Jev"
                            RUN_STATE["progress_percent"] = 55
                        elif "Evaluando clusters con Jev" in line or "typesafe" in lower_line:
                            RUN_STATE["current_step"] = "Evaluando clusters con Jev (TypeSafe System 1)"
                            RUN_STATE["progress_percent"] = 72
                        elif "[Scraper Híbrido]" in line or "Raspando evidencia" in line or "🕸️" in line:
                            RUN_STATE["current_step"] = "Scraper Híbrido: Extrayendo contenido web del Top 10"
                            RUN_STATE["progress_percent"] = 82
                        elif "[3/3]" in line or "Generando Adaptación" in line:
                            RUN_STATE["current_step"] = "Fase 3/3: Adaptación Editorial y Embudo 30X"
                            RUN_STATE["progress_percent"] = 90
                        elif "Reporte guardado con éxito" in line or "💾" in line:
                            RUN_STATE["current_step"] = "Guardando reporte y persistiendo en SQLite"
                            RUN_STATE["progress_percent"] = 96
                        elif "Ciclo multi-agente completado" in line:
                            RUN_STATE["current_step"] = "Ciclo multi-agente finalizado"
                            RUN_STATE["progress_percent"] = 95

                        RUN_STATE["duration_seconds"] = round(time.time() - start_time, 1)
                        RUN_STATE["logs"].append({
                            "id": log_id,
                            "time": now_str,
                            "text": line,
                            "level": level,
                        })
                        if len(RUN_STATE["logs"]) > 1000:
                            RUN_STATE["logs"] = RUN_STATE["logs"][-1000:]

            proc.wait()
            end_time = time.time()
            with RUN_LOCK:
                CURRENT_PROCESS = None
                RUN_STATE["is_running"] = False
                RUN_STATE["finished_at"] = datetime.now(timezone.utc).isoformat()
                RUN_STATE["duration_seconds"] = round(end_time - start_time, 1)
                RUN_STATE["last_run"] = RUN_STATE["finished_at"]
                if proc.returncode == 0:
                    RUN_STATE["last_status"] = "success"
                    RUN_STATE["current_step"] = f"Completado exitosamente en {RUN_STATE['duration_seconds']}s"
                    RUN_STATE["progress_percent"] = 100
                    RUN_STATE["logs"].append({
                        "id": log_id + 1,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "text": f"✨ [{label}] Proceso finalizado con código 0 ({RUN_STATE['duration_seconds']}s). Datos actualizados.",
                        "level": "success",
                    })
                elif RUN_STATE["last_status"] == "cancelled" or proc.returncode in (-15, -9, 143):
                    RUN_STATE["last_status"] = "cancelled"
                    RUN_STATE["current_step"] = f"Cancelado por el usuario ({RUN_STATE['duration_seconds']}s)"
                    RUN_STATE["logs"].append({
                        "id": log_id + 1,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "text": f"🛑 [{label}] Proceso detenido por el usuario.",
                        "level": "warning",
                    })
                else:
                    RUN_STATE["last_status"] = "error"
                    RUN_STATE["current_step"] = f"Error en ejecución (código {proc.returncode})"
                    RUN_STATE["last_error"] = f"El comando terminó con código de error {proc.returncode}"
                    RUN_STATE["logs"].append({
                        "id": log_id + 1,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "text": f"❌ [{label}] Finalizó con código de error {proc.returncode}.",
                        "level": "error",
                    })
        except Exception as ex:
            logger.exception("Error ejecutando subproceso: %s", ex)
            with RUN_LOCK:
                CURRENT_PROCESS = None
                RUN_STATE["is_running"] = False
                RUN_STATE["last_status"] = "error"
                RUN_STATE["current_step"] = f"Excepción: {ex}"
                RUN_STATE["last_error"] = str(ex)
                RUN_STATE["logs"].append({
                    "id": log_id + 1,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "text": f"💥 Excepción en ejecución: {ex}",
                    "level": "error",
                })

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return True


def trigger_background_run() -> bool:
    """Ejecuta el pipeline completo de Sonar (run-all --top 10) con streaming en tiempo real."""
    return start_process_run(["run-all", "--top", "10"], label="Actualizar Sonar")


class RadarHTTPHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para la API JSON y la interfaz web."""

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_content: str, status: int = 200) -> None:
        payload = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 0. API: Enfoques de Búsqueda
        if path == "/api/focuses":
            from pipeline.focuses import load_focuses
            focuses = load_focuses()
            self._send_json({"focuses": [f.model_dump() for f in focuses]})
            return

        # 0.1 API: Base de Conocimiento - Listar fuentes
        if path == "/api/knowledge":
            from pipeline.knowledge import list_knowledge_sources
            sources = list_knowledge_sources()
            self._send_json({"sources": [s.model_dump() for s in sources]})
            return

        # 0.2 API: Feeds sindicados de RSS.app
        if path == "/api/rssapp/feeds":
            from pipeline.rssapp_manager import load_rssapp_feeds
            feeds = load_rssapp_feeds(force_reload=True)
            self._send_json({"feeds": [f.model_dump() for f in feeds]})
            return

        # 0.3 API: Bibliografía de fuentes y orígenes de datos
        if path == "/api/bibliography":
            data = get_bibliography_data()
            self._send_json(data)
            return

        # 0.4 API: Búsqueda web automatizada (GET test / query)
        if path in ("/api/websearch/test", "/api/websearch/query"):
            q_list = params.get("q", []) or params.get("query", [])
            query = q_list[0].strip() if q_list else ""
            limit_val = params.get("limit", ["8"])[0]
            try:
                limit = int(limit_val)
            except ValueError:
                limit = 8
            if not query:
                self._send_json({"error": "La consulta de búsqueda 'q' es obligatoria."}, status=400)
                return
            try:
                from sources.websearch import search_web_engine
                items = search_web_engine(query, limit=limit)
                self._send_json({
                    "query": query,
                    "total": len(items),
                    "results": [
                        {
                            "id": it.id,
                            "titulo": it.titulo,
                            "resumen": it.resumen,
                            "url": it.url,
                            "autor": it.autor,
                            "fecha": it.fecha,
                            "metricas": it.metricas,
                        }
                        for it in items
                    ],
                })
            except Exception as e:
                logger.exception("Error en búsqueda web GET: %s", e)
                self._send_json({"error": f"Error buscando en la web: {e}"}, status=500)
            return

        # 0.2 API: Base de Conocimiento - Detalle por ID
        if path.startswith("/api/knowledge/") and not path.endswith("/search"):
            source_id = path.replace("/api/knowledge/", "").strip("/")
            from pipeline.knowledge.vector_store import VectorStore
            store = VectorStore()
            res = store.get_source_by_id(source_id)
            if res:
                src, chunks = res
                self._send_json({
                    "source": src.model_dump(),
                    "chunks": [c.model_dump() for c in chunks],
                })
            else:
                self._send_json({"error": "Recurso no encontrado"}, status=404)
            return

        # 1. API: Listar reportes
        if path == "/api/reports":
            self._send_json({"reports": list_available_reports()})
            return

        # 2. API: Reporte más reciente
        if path == "/api/report/latest":
            data = load_latest_report()
            if data:
                self._send_json(data)
            else:
                self._send_json({"error": "No se encontraron reportes generados aún."}, status=404)
            return

        # 3. API: Reporte específico (/api/report/<nombre>)
        if path.startswith("/api/report/"):
            filename = path.replace("/api/report/", "")
            if not filename.endswith(".json"):
                filename += ".json"
            data = load_report_by_name(filename)
            if data:
                self._send_json(data)
            else:
                self._send_json({"error": f"Reporte '{filename}' no encontrado."}, status=404)
            return

        # 4. API: Explorador de ítems / base de datos
        if path == "/api/items":
            fuente = params.get("fuente", [None])[0]
            search = params.get("search", [None])[0]
            limit_str = params.get("limit", ["100"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 100
            items = query_db_items(fuente=fuente, search=search, limit=limit)
            self._send_json({"total": len(items), "items": items})
            return

        # 5. API: Estado de ejecución y streaming de logs
        if path == "/api/status":
            with RUN_LOCK:
                if RUN_STATE["is_running"] and RUN_STATE.get("started_at"):
                    try:
                        started = datetime.fromisoformat(RUN_STATE["started_at"])
                        RUN_STATE["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 1)
                    except Exception:
                        pass

                since_id_str = params.get("since", [None])[0]
                if since_id_str is not None:
                    try:
                        since_id = int(since_id_str)
                        logs_to_send = [l for l in RUN_STATE["logs"] if l["id"] > since_id]
                    except ValueError:
                        logs_to_send = RUN_STATE["logs"]
                else:
                    logs_to_send = RUN_STATE["logs"]

                response_payload = dict(RUN_STATE)
                response_payload["logs"] = logs_to_send
                response_payload["total_logs"] = len(RUN_STATE["logs"])
                self._send_json(response_payload)
            return

        # 5.1 API: Agentes - Listar runs y auditoría
        if path == "/api/agents/runs":
            db = Database()
            runs = db.get_runs(limit=20)
            audit = db.get_audit_logs(limit=50)
            self._send_json({"runs": runs, "audit_log": audit})
            return

        # 5.2 API: Agentes - Listar narrativas y memoria histórica
        if path == "/api/agents/narratives":
            db = Database()
            narratives = db.get_narratives(limit=50)
            self._send_json({"narratives": narratives, "total": len(narratives)})
            return

        # 5.3 API: Chatbot - Logs recientes
        if path == "/api/chat/logs":
            db = Database()
            logs = db.get_chat_logs(limit=50)
            self._send_json({"logs": logs, "total": len(logs)})
            return

        # 5.3b API: Scraper Híbrido - Estado de motores
        if path == "/api/scraper/status":
            try:
                from pipeline.scraper import HybridScraper
                scraper = HybridScraper()
                self._send_json(scraper.get_status())
            except Exception as e:
                logger.exception("Error al consultar estado del scraper: %s", e)
                self._send_json({"error": str(e)}, status=500)
            return

        # 5.4 API: Borradores - Listar borradores
        if path == "/api/drafts":
            from drafts.manager import DraftManager
            dm = DraftManager()
            qs = parse_qs(parsed.query)
            estado = qs.get("estado", [None])[0]
            drafts = dm.list_drafts(estado=estado)
            self._send_json({"drafts": drafts, "total": len(drafts)})
            return

        # 5.5 API: Borradores - Detalle de borrador
        if path.startswith("/api/drafts/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                draft_id = int(parts[2])
                from drafts.manager import DraftManager
                dm = DraftManager()
                d = dm.get_draft(draft_id)
                if d:
                    self._send_json(d)
                else:
                    self._send_json({"error": f"Borrador #{draft_id} no encontrado"}, status=404)
                return

        # 6. Servir Frontend Next.js estático (frontend/out) o template de reserva
        frontend_out = get_base_dir() / "frontend" / "out"
        if frontend_out.exists():
            rel_path = path.lstrip("/")
            if not rel_path or rel_path == "index.html":
                target_file = frontend_out / "index.html"
            else:
                target_file = frontend_out / rel_path
                if target_file.is_dir() and (target_file / "index.html").is_file():
                    target_file = target_file / "index.html"
                elif not target_file.is_file():
                    if (frontend_out / f"{rel_path}.html").is_file():
                        target_file = frontend_out / f"{rel_path}.html"
                    elif (frontend_out / "index.html").is_file() and not "." in rel_path:
                        target_file = frontend_out / "index.html"

            if target_file.is_file():
                import mimetypes
                content_type, _ = mimetypes.guess_type(str(target_file))
                content_type = content_type or "application/octet-stream"
                if content_type.startswith("text/") or content_type in ["application/javascript", "application/json"]:
                    content_type += "; charset=utf-8"
                with open(target_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return

        # Fallback a plantilla de reserva
        if path in ["/", "/index.html"]:
            template_path = get_base_dir() / "web" / "templates" / "index.html"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._send_html(content)
            else:
                self._send_html("<h1>Error: plantilla index.html no encontrada</h1>", status=500)
            return

        # Ruta no encontrada
        self.send_error(404, "Ruta no encontrada")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # Disparar ejecución en segundo plano
        if path == "/api/run":
            started = trigger_background_run()
            if started:
                self._send_json({"status": "started", "message": "Radar iniciado en segundo plano."})
            else:
                self._send_json({"status": "already_running", "message": "Una ejecución ya está en curso."}, status=409)
            return

        # Cancelar ejecución en segundo plano
        if path == "/api/run/cancel":
            cancelled = cancel_current_run()
            if cancelled:
                self._send_json({"status": "cancelled", "message": "Ejecución cancelada con éxito."})
            else:
                self._send_json({"status": "not_running", "message": "No hay ningún proceso activo para cancelar."}, status=400)
            return

        # Crear nuevo enfoque de búsqueda
        if path == "/api/focuses":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.focuses import add_focus
                new_f = add_focus(
                    nombre=data.get("nombre", ""),
                    categoria=data.get("categoria", "general"),
                    keywords=data.get("keywords", []),
                    descripcion=data.get("descripcion", ""),
                )
                self._send_json({"status": "created", "focus": new_f.model_dump()}, status=201)
            except Exception as e:
                self._send_json({"error": f"Error al procesar solicitud: {e}"}, status=400)
            return

        # Alternar estado activo de enfoque (/api/focuses/<id>/toggle)
        if path.startswith("/api/focuses/") and path.endswith("/toggle"):
            focus_id = path.replace("/api/focuses/", "").replace("/toggle", "")
            from pipeline.focuses import toggle_focus
            updated = toggle_focus(focus_id)
            if updated:
                self._send_json({"status": "updated", "focus": updated.model_dump()})
            else:
                self._send_json({"error": f"Enfoque '{focus_id}' no encontrado."}, status=404)
            return

        # Ingestar recurso a la base de conocimiento con solicitud del usuario
        if path == "/api/knowledge/ingest":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.knowledge import ingest_knowledge_resource
                url = data.get("url", "").strip()
                solicitud = data.get("solicitud", "").strip() or "Extraer ganchos y estructura de retención"
                tipo = data.get("tipo", "youtube")
                titulo = data.get("titulo")
                autor = data.get("autor")
                modo = data.get("modo", "completo")
                image_data = data.get("image_data")
                images_data = data.get("images_data")
                filenames = data.get("filenames")

                if isinstance(image_data, list):
                    images_data = image_data
                    image_data = images_data[0] if images_data else None

                if not url and not image_data and not images_data:
                    self._send_json({"error": "La URL del recurso o una imagen es obligatoria."}, status=400)
                    return

                if not url and (image_data or images_data):
                    count = len(images_data) if images_data else 1
                    url = f"pool_{count}_imagenes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                if images_data and len(images_data) > 1:
                    tipo = "image_pool"

                src, prof = ingest_knowledge_resource(
                    url_o_path=url,
                    solicitud_usuario=solicitud,
                    tipo=tipo,
                    modo=modo,
                    titulo=titulo,
                    autor=autor,
                    image_data=image_data,
                    images_data=images_data,
                    filenames=filenames,
                )
                self._send_json({
                    "status": "success",
                    "source": src.model_dump(),
                    "profile": prof.model_dump(),
                }, status=201)
            except Exception as e:
                logger.exception("Error al procesar conocimiento: %s", e)
                self._send_json({"error": f"Error al procesar recurso: {e}"}, status=500)
            return

        # Consulta en vivo de búsqueda web automatizada
        if path in ("/api/websearch/query", "/api/websearch/test"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                query = (
                    data.get("query")
                    or data.get("q")
                    or data.get("tema")
                    or data.get("headline")
                    or ""
                ).strip()
                limit = int(data.get("limit", 8))
                if not query:
                    self._send_json({"error": "La consulta de búsqueda es obligatoria."}, status=400)
                    return
                from sources.websearch import search_web_engine
                items = search_web_engine(query, limit=limit)
                self._send_json({
                    "query": query,
                    "total": len(items),
                    "results": [
                        {
                            "id": it.id,
                            "titulo": it.titulo,
                            "resumen": it.resumen,
                            "url": it.url,
                            "autor": it.autor,
                            "fecha": it.fecha,
                            "metricas": it.metricas,
                        }
                        for it in items
                    ],
                })
            except Exception as e:
                self._send_json({"error": f"Error en búsqueda web: {e}"}, status=500)
            return

        # Búsqueda semántica en la base de conocimiento
        if path == "/api/knowledge/search":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.knowledge import search_knowledge_base
                query = data.get("query", "").strip()
                top_k = int(data.get("top_k", 5))
                tag = data.get("tag")
                results = search_knowledge_base(query=query, top_k=top_k, tag_filter=tag)
                self._send_json({"query": query, "total": len(results), "results": results})
            except Exception as e:
                self._send_json({"error": f"Error en búsqueda vectorial: {e}"}, status=400)
            return

        # Evaluación en tiempo real para el Playground de JEV
        if path == "/api/playground/eval":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.playground import evaluate_playground_item
                tema = (
                    data.get("tema")
                    or data.get("headline")
                    or data.get("titular")
                    or data.get("query")
                    or data.get("titulo")
                    or ""
                ).strip()
                if not tema:
                    self._send_json({"error": "El tema o titular es obligatorio."}, status=400)
                    return
                fuentes = data.get("fuentes", ["HackerNews", "YouTube"])
                vph = float(data.get("vistas_por_hora", 150.0))
                titulos = data.get("titulos_muestra") or [tema]
                telemetry = evaluate_playground_item(
                    tema=tema,
                    fuentes=fuentes,
                    vistas_por_hora=vph,
                    titulos_muestra=titulos,
                )
                self._send_json(telemetry.model_dump())
            except Exception as e:
                logger.exception("Error en evaluación de playground: %s", e)
                self._send_json({"error": f"Error evaluando con Jev: {e}"}, status=500)
            return

        # Registrar nuevo feed de RSS.app
        if path == "/api/rssapp/feeds":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.rssapp_manager import add_rssapp_feed
                url = data.get("url", "").strip()
                nombre = data.get("nombre", "").strip() or "Feed RSS.app"
                plataforma = data.get("plataforma", "General")
                enfoque_id = data.get("enfoque_id", "polemicas-labs")

                if not url:
                    self._send_json({"error": "La URL del feed de RSS.app es requerida."}, status=400)
                    return

                new_feed = add_rssapp_feed(url=url, nombre=nombre, plataforma=plataforma, enfoque_id=enfoque_id)
                self._send_json({"status": "created", "feed": new_feed.model_dump()}, status=201)
            except Exception as e:
                self._send_json({"error": f"Error al registrar feed: {e}"}, status=400)
            return

        # Alternar estado activo de feed RSS.app (/api/rssapp/feeds/<id>/toggle)
        if path.startswith("/api/rssapp/feeds/") and path.endswith("/toggle"):
            feed_id = path.replace("/api/rssapp/feeds/", "").replace("/toggle", "").strip("/")
            from pipeline.rssapp_manager import toggle_rssapp_feed
            updated = toggle_rssapp_feed(feed_id)
            if updated:
                self._send_json({"status": "updated", "feed": updated.model_dump()})
            else:
                self._send_json({"error": f"Feed '{feed_id}' no encontrado."}, status=404)
            return

        # Probar conexión en vivo a feed RSS.app
        if path == "/api/rssapp/test":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.rssapp_manager import verify_rssapp_feed_connection
                url = data.get("url", "").strip()
                if not url:
                    self._send_json({"error": "La URL del feed es requerida."}, status=400)
                    return
                res = verify_rssapp_feed_connection(url)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": f"Error probando feed: {e}"}, status=400)
            return

        # Disparar ciclo de 12h de agentes
        if path == "/api/agents/cycle":
            started = start_process_run(["cycle"], label="Ciclo de Agentes 12h")
            if started:
                self._send_json({"status": "started", "message": "Ciclo multi-agente iniciado en segundo plano."}, status=202)
            else:
                self._send_json({"status": "already_running", "message": "Una ejecución ya está en curso."}, status=409)
            return

        # Disparar backfill histórico de 90 días
        if path == "/api/agents/backfill":
            started = start_process_run(["backfill", "--days", "90"], label="Backfill Histórico 90d")
            if started:
                self._send_json({"status": "started", "message": "Backfill histórico de 90 días iniciado en segundo plano."}, status=202)
            else:
                self._send_json({"status": "already_running", "message": "Una ejecución ya está en curso."}, status=409)
            return

        # Consulta Chatbot RAG
        if path == "/api/chat/ask":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                pregunta = (data.get("pregunta") or data.get("query") or "").strip()
                if not pregunta:
                    self._send_json({"error": "La pregunta es obligatoria."}, status=400)
                    return
                from chat.service import ChatService
                svc = ChatService()
                res = svc.ask(
                    pregunta=pregunta,
                    no_cache=data.get("no_cache", False),
                    force_level=data.get("force_level"),
                    show_sources=data.get("show_sources", True),
                )
                self._send_json(res)
            except Exception as e:
                logger.exception("Error al procesar consulta de chat: %s", e)
                self._send_json({"error": f"Error al procesar consulta: {e}"}, status=500)
            return

        # Extracción Web con Scraper Híbrido
        if path == "/api/scraper/extract":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                url = (data.get("url") or "").strip()
                if not url:
                    self._send_json({"error": "La URL es obligatoria."}, status=400)
                    return
                mode = data.get("mode", "auto")
                from pipeline.scraper import HybridScraper
                scraper = HybridScraper()
                res = scraper.scrape(url=url, mode=mode)
                self._send_json(res.to_dict())
            except Exception as e:
                logger.exception("Error en extracción web: %s", e)
                self._send_json({"error": f"Error en extracción web: {e}"}, status=500)
            return

        # Crear nuevo borrador
        if path == "/api/drafts":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from drafts.manager import DraftManager
                dm = DraftManager()
                res = dm.create_draft(
                    narrative_id=data.get("narrative_id"),
                    titulo=data.get("titulo"),
                    formato=data.get("formato", "video_corto"),
                    gancho=data.get("gancho", "opinion"),
                    autor=data.get("autor", "30X Media"),
                    evidencia=data.get("evidencia", []),
                )
                self._send_json(res, status=201)
            except Exception as e:
                logger.exception("Error al crear borrador: %s", e)
                self._send_json({"error": f"Error al crear borrador: {e}"}, status=500)
            return

        # Actualizar estado de borrador
        if path.startswith("/api/drafts/") and path.endswith("/status"):
            try:
                parts = path.strip("/").split("/")
                draft_id = int(parts[2])
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                nuevo_estado = data.get("estado", "").strip()
                from drafts.manager import DraftManager
                dm = DraftManager()
                res = dm.update_status(draft_id, nuevo_estado)
                self._send_json(res)
            except ValueError as ve:
                self._send_json({"error": str(ve)}, status=400)
            except Exception as e:
                logger.exception("Error al actualizar estado del borrador: %s", e)
                self._send_json({"error": f"Error al actualizar estado: {e}"}, status=500)
            return

        # Actualizar contenido markdown de borrador (POST o PUT /api/drafts/<id>)
        if path.startswith("/api/drafts/") and not path.endswith("/status"):
            try:
                parts = path.strip("/").split("/")
                draft_id = int(parts[2])
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from drafts.manager import DraftManager
                dm = DraftManager()
                new_body = data.get("body", data.get("content", ""))
                new_title = data.get("titulo")
                author = data.get("autor")
                res = dm.update_draft_content(draft_id, new_body=new_body, new_title=new_title, author=author)
                self._send_json(res)
            except ValueError as ve:
                self._send_json({"error": str(ve)}, status=400)
            except Exception as e:
                logger.exception("Error al actualizar contenido del borrador: %s", e)
                self._send_json({"error": f"Error al actualizar contenido: {e}"}, status=500)
            return

        self.send_error(404, "Ruta no encontrada")

    def do_PUT(self) -> None:
        self.do_POST()

    def do_PATCH(self) -> None:
        # Permitir PATCH para toggle también
        self.do_POST()

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/rssapp/feeds/"):
            feed_id = path.replace("/api/rssapp/feeds/", "").strip("/")
            from pipeline.rssapp_manager import delete_rssapp_feed
            deleted = delete_rssapp_feed(feed_id)
            if deleted:
                self._send_json({"status": "deleted", "id": feed_id})
            else:
                self._send_json({"error": f"Feed '{feed_id}' no encontrado."}, status=404)
            return

        if path.startswith("/api/focuses/"):
            focus_id = path.replace("/api/focuses/", "").strip("/")
            from pipeline.focuses import delete_focus
            deleted = delete_focus(focus_id)
            if deleted:
                self._send_json({"status": "deleted", "id": focus_id})
            else:
                self._send_json({"error": f"Enfoque '{focus_id}' no encontrado."}, status=404)
            return

        if path.startswith("/api/knowledge/"):
            source_id = path.replace("/api/knowledge/", "").strip("/")
            from pipeline.knowledge.vector_store import VectorStore
            store = VectorStore()
            deleted = store.delete_source(source_id)
            if deleted:
                self._send_json({"status": "deleted", "id": source_id})
            else:
                self._send_json({"error": f"Recurso '{source_id}' no encontrado."}, status=404)
            return

        self.send_error(404, "Ruta no encontrada")

    def log_message(self, format: str, *args: Any) -> None:
        # Silenciar logs ruidosos de polling
        if args and any(p in str(args[0]) for p in ["/api/status"]):
            return
        super().log_message(format, *args)


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Inicia el servidor web en el host y puerto especificados."""
    server_address = (host, port)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, RadarHTTPHandler)
    print(f"\n🚀 Servidor Web Radar30X activo en:")
    print(f"   👉 http://localhost:{port}")
    print(f"   👉 http://127.0.0.1:{port}")
    print("   Presiona Ctrl+C para detener el servidor.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor web detenido.")
        httpd.server_close()
