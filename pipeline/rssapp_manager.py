"""Gestor y persistencia de feeds sindicados generados con RSS.app (https://rss.app/es).

Permite conectar feeds de Twitter/X, TikTok, LinkedIn, YouTube y sitios web
para alimentar el Radar de Contenido 30X con validación multi-fuente en tiempo real.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
import httpx
import feedparser

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "rssapp_feeds.json"


class RSSAppFeed(BaseModel):
    """Modelo estructurado para un feed generado en RSS.app."""

    id: str = Field(description="Identificador único del feed (ej. rssapp-twitter-ai)")
    nombre: str = Field(description="Nombre descriptivo asignado por el usuario")
    url: str = Field(description="URL pública del feed en RSS.app (XML o JSON)")
    plataforma: Literal["Twitter/X", "TikTok", "LinkedIn", "YouTube", "Web", "General"] = Field(
        default="General",
        description="Red social o plataforma de origen",
    )
    enfoque_id: str = Field(
        default="polemicas-labs",
        description="ID del enfoque de búsqueda temático al que está vinculado",
    )
    activo: bool = Field(default=True, description="Si el feed está activo para ingesta")
    ultimo_sync: Optional[str] = Field(default=None, description="Fecha ISO de la última sincronización")
    total_items_capturados: int = Field(default=0, description="Total histórico de ítems procesados")
    creado_en: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


DEFAULT_FEEDS: List[Dict[str, Any]] = [
    {
        "id": "rssapp-twitter-ai-leaders",
        "nombre": "X / Twitter — Líderes de Labs & Seguridad (Sam Altman, Dario Amodei, Karpathy)",
        "url": "https://rss.app/feeds/twitter_ai_leaders_sample.xml",
        "plataforma": "Twitter/X",
        "enfoque_id": "polemicas-labs",
        "activo": True,
        "ultimo_sync": None,
        "total_items_capturados": 18,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "rssapp-tiktok-ia-herramientas",
        "nombre": "TikTok — IA Viral, Automatizaciones y Herramientas 2026",
        "url": "https://rss.app/feeds/tiktok_ia_tools_sample.xml",
        "plataforma": "TikTok",
        "enfoque_id": "agentes-operaciones",
        "activo": True,
        "ultimo_sync": None,
        "total_items_capturados": 24,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "rssapp-linkedin-exec-latam",
        "nombre": "LinkedIn — CEOs y Directores de Tecnología en LatAm",
        "url": "https://rss.app/feeds/linkedin_tech_latam_sample.xml",
        "plataforma": "LinkedIn",
        "enfoque_id": "ceo-desarrollo",
        "activo": True,
        "ultimo_sync": None,
        "total_items_capturados": 12,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "rssapp-benchmarks-feed",
        "nombre": "Web Monitor — Evaluaciones y SWE-bench Tracking",
        "url": "https://rss.app/feeds/swe_bench_evals_sample.xml",
        "plataforma": "Web",
        "enfoque_id": "benchmarks-race",
        "activo": True,
        "ultimo_sync": None,
        "total_items_capturados": 9,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "rssapp-youtube-ai-devs",
        "nombre": "YouTube — AI Engineering, Agentes y Arquitectura de Sistemas",
        "url": "https://rss.app/feeds/youtube_ai_engineering_sample.xml",
        "plataforma": "YouTube",
        "enfoque_id": "graphrag-knowledge",
        "activo": True,
        "ultimo_sync": None,
        "total_items_capturados": 22,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    },
]


def _get_data_file() -> Path:
    if "RSSAPP_FEEDS_PATH" in os.environ:
        return Path(os.environ["RSSAPP_FEEDS_PATH"])
    return Path(DATA_FILE)


_IN_MEMORY_FEEDS: Optional[List[RSSAppFeed]] = None


def load_rssapp_feeds(force_reload: bool = False) -> List[RSSAppFeed]:
    """Carga la lista de feeds registrados desde data/rssapp_feeds.json o memoria."""
    global _IN_MEMORY_FEEDS
    if not force_reload and _IN_MEMORY_FEEDS is not None:
        return list(_IN_MEMORY_FEEDS)

    data_file = _get_data_file()
    if not data_file.exists():
        default_list = [RSSAppFeed(**f) for f in DEFAULT_FEEDS]
        save_rssapp_feeds(default_list)
        _IN_MEMORY_FEEDS = default_list
        return list(_IN_MEMORY_FEEDS)

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            raw_list = json.load(f)
            _IN_MEMORY_FEEDS = [RSSAppFeed(**item) for item in raw_list]
            return list(_IN_MEMORY_FEEDS)
    except Exception as exc:
        logger.error("Error al cargar feeds de RSS.app (%s). Usando valores por defecto.", exc)
        _IN_MEMORY_FEEDS = [RSSAppFeed(**f) for f in DEFAULT_FEEDS]
        return list(_IN_MEMORY_FEEDS)


def save_rssapp_feeds(feeds: List[RSSAppFeed]) -> None:
    """Guarda la lista de feeds en disco con formato legible o en memoria si es de solo lectura."""
    global _IN_MEMORY_FEEDS
    _IN_MEMORY_FEEDS = list(feeds)
    data_file = _get_data_file()
    try:
        os.makedirs(data_file.parent, exist_ok=True)
        payload = [f.model_dump() for f in feeds]
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("No se pudo escribir archivo de feeds de RSS.app (%s). Guardado en memoria.", exc)



def add_rssapp_feed(
    url: str,
    nombre: str,
    plataforma: str = "General",
    enfoque_id: str = "polemicas-labs",
) -> RSSAppFeed:
    """Agrega un nuevo feed de RSS.app con detección automática de plataforma si no se especifica."""
    feeds = load_rssapp_feeds()
    cleaned_url = url.strip()

    # Detección automática de plataforma según URL si es 'General'
    if plataforma == "General":
        lower_url = cleaned_url.lower()
        if "twitter" in lower_url or "/x/" in lower_url:
            plataforma = "Twitter/X"
        elif "tiktok" in lower_url:
            plataforma = "TikTok"
        elif "linkedin" in lower_url:
            plataforma = "LinkedIn"
        elif "youtube" in lower_url:
            plataforma = "YouTube"
        else:
            plataforma = "Web"

    feed_id = f"rssapp-{hashlib.md5(cleaned_url.encode()).hexdigest()[:8]}"

    # Si ya existe, actualizarlo
    for idx, existing in enumerate(feeds):
        if existing.url == cleaned_url or existing.id == feed_id:
            existing.nombre = nombre
            existing.plataforma = plataforma
            existing.enfoque_id = enfoque_id
            existing.activo = True
            save_rssapp_feeds(feeds)
            return existing

    new_feed = RSSAppFeed(
        id=feed_id,
        nombre=nombre.strip(),
        url=cleaned_url,
        plataforma=plataforma,
        enfoque_id=enfoque_id,
        activo=True,
    )
    feeds.append(new_feed)
    save_rssapp_feeds(feeds)
    return new_feed


def toggle_rssapp_feed(feed_id: str) -> Optional[RSSAppFeed]:
    """Invierte el estado activo/inactivo de un feed."""
    feeds = load_rssapp_feeds()
    target = None
    for f in feeds:
        if f.id == feed_id:
            f.activo = not f.activo
            target = f
            break
    if target:
        save_rssapp_feeds(feeds)
    return target


def delete_rssapp_feed(feed_id: str) -> bool:
    """Elimina un feed por ID."""
    feeds = load_rssapp_feeds()
    initial_len = len(feeds)
    feeds = [f for f in feeds if f.id != feed_id]
    if len(feeds) < initial_len:
        save_rssapp_feeds(feeds)
        return True
    return False


def verify_rssapp_feed_connection(url: str, timeout: float = 8.0) -> Dict[str, Any]:
    """Realiza una prueba rápida de conexión al feed y extrae hasta 3 publicaciones de muestra."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Radar30XBot/1.0"}) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return {
                    "ok": False,
                    "error": f"El servidor de RSS.app retornó código HTTP {resp.status_code}",
                    "muestra": [],
                }

            # Intentar parsear como JSON Feed primero
            try:
                data = resp.json()
                if "items" in data:
                    muestra = [
                        {
                            "titulo": it.get("title", ""),
                            "url": it.get("url", ""),
                            "fecha": it.get("date_published", ""),
                        }
                        for it in data["items"][:3]
                    ]
                    return {
                        "ok": True,
                        "tipo": "JSON Feed",
                        "titulo_feed": data.get("title", "Feed RSS.app"),
                        "muestra": muestra,
                    }
            except Exception:
                pass

            # Parsear como XML Feed con feedparser
            feed = feedparser.parse(resp.content)
            if not feed.entries:
                return {
                    "ok": False,
                    "error": "No se encontraron publicaciones en el feed provisto.",
                    "muestra": [],
                }

            muestra = [
                {
                    "titulo": getattr(e, "title", "Sin título"),
                    "url": getattr(e, "link", url),
                    "fecha": getattr(e, "published", ""),
                }
                for e in feed.entries[:3]
            ]
            return {
                "ok": True,
                "tipo": "XML RSS 2.0",
                "titulo_feed": getattr(feed.feed, "title", "Feed RSS.app"),
                "muestra": muestra,
            }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Error de conexión: {str(exc)}",
            "muestra": [],
        }


# Alias retrocompatible
test_feed_connection = verify_rssapp_feed_connection

