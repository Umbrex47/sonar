"""Adaptador de fuente para RSS.app (https://rss.app/es).

Ingesta feeds sindicados generados en RSS.app para Twitter/X, TikTok,
LinkedIn, YouTube y sitios web dinámicos sin APIs propietarias ni scrapers frágiles.
Aporta validación cruzada multi-fuente y señales virales de redes sociales en tiempo real.
"""

from datetime import datetime, timezone
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional
import feedparser
import httpx

from sources.base import BaseSource, RawItem
from pipeline.rssapp_manager import load_rssapp_feeds, save_rssapp_feeds, RSSAppFeed

logger = logging.getLogger(__name__)


def clean_social_text(text: str) -> str:
    """Limpia URLs incrustadas, menciones repetitivas y exceso de hashtags en textos sociales."""
    cleaned = re.sub(r"https?://\S+", "", text)
    cleaned = re.sub(r"pic\.twitter\.com/\S+", "", cleaned)
    cleaned = re.sub(r"#\w+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class RSSAppSource(BaseSource):
    """Adaptador de ingesta de contenido para feeds generados con RSS.app."""

    name: str = "RSS.app"

    def fetch(self, limit: int = 40) -> List[RawItem]:
        """Recolecta publicaciones recientes desde todos los feeds activos de RSS.app."""
        feeds = load_rssapp_feeds()
        active_feeds = [f for f in feeds if f.activo]
        if not active_feeds:
            logger.info("No hay feeds activos de RSS.app configurados.")
            return []

        items: List[RawItem] = []
        limit_per_feed = max(5, limit // len(active_feeds))
        now_ts = time.time()
        max_age_seconds = 8 * 86400  # 8 días de frescura

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Radar30XBot/1.0 (RSS.app syndication)",
            "Accept": "application/rss+xml, application/xml, application/json, text/xml",
        }

        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            for feed in active_feeds:
                feed_items_count = 0
                try:
                    resp = client.get(feed.url)
                    if resp.status_code != 200:
                        logger.warning("Feed RSS.app '%s' retornó HTTP %d", feed.nombre, resp.status_code)
                        continue

                    # 1. Intentar parsear como JSON Feed
                    is_json_feed = False
                    try:
                        json_data = resp.json()
                        if isinstance(json_data, dict) and "items" in json_data:
                            is_json_feed = True
                            for entry in json_data["items"][:limit_per_feed]:
                                raw = self._parse_json_entry(entry, feed, now_ts, max_age_seconds)
                                if raw:
                                    items.append(raw)
                                    feed_items_count += 1
                    except Exception:
                        is_json_feed = False

                    # 2. Si no es JSON, parsear con feedparser (XML RSS 2.0 / Atom)
                    if not is_json_feed:
                        parsed = feedparser.parse(resp.content)
                        for entry in parsed.entries[:limit_per_feed]:
                            raw = self._parse_xml_entry(entry, feed, now_ts, max_age_seconds)
                            if raw:
                                items.append(raw)
                                feed_items_count += 1

                    # Actualizar estadísticas del feed
                    feed.ultimo_sync = datetime.now(timezone.utc).isoformat()
                    feed.total_items_capturados += feed_items_count

                except Exception as exc:
                    logger.warning("Error al consultar feed RSS.app '%s' (%s): %s", feed.nombre, feed.url, exc)

        # Guardar timestamps de sincronización actualizados
        try:
            save_rssapp_feeds(feeds)
        except Exception as exc:
            logger.warning("No se pudieron guardar métricas de feeds RSS.app: %s", exc)

        logger.info("RSS.app: %d ítems recolectados desde %d feeds activos.", len(items), len(active_feeds))
        return items

    def _parse_xml_entry(
        self,
        entry: Any,
        feed: RSSAppFeed,
        now_ts: float,
        max_age_seconds: float,
    ) -> Optional[RawItem]:
        """Extrae y valida un ítem desde un feed XML de RSS.app."""
        title = getattr(entry, "title", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        link = getattr(entry, "link", "").strip()

        if not title and not summary:
            return None

        # Si el título es muy largo o genérico (común en tweets), usar el resumen limpio
        if not title:
            title = clean_social_text(summary)[:120]
        else:
            title = clean_social_text(title)

        if len(title) < 8:
            return None

        # Filtro de recencia
        pub_parsed = getattr(entry, "published_parsed", None)
        pub_iso = datetime.now(timezone.utc).isoformat()
        if pub_parsed:
            try:
                pub_ts = time.mktime(pub_parsed)
                if now_ts - pub_ts > max_age_seconds:
                    return None
                pub_iso = datetime.fromtimestamp(pub_ts, timezone.utc).isoformat()
            except Exception:
                pass

        # Determinar formato según plataforma
        if feed.plataforma == "TikTok":
            formato = "video_corto"
        elif feed.plataforma == "Twitter/X":
            formato = "hilo"
        elif feed.plataforma == "LinkedIn":
            formato = "carousel"
        else:
            formato = "articulo"

        author = getattr(entry, "author", "") or feed.nombre.split("—")[0].strip()
        item_id = hashlib.sha256(f"rssapp:{feed.id}:{link or title}".encode()).hexdigest()[:16]

        return RawItem(
            id=item_id,
            fuente=f"RSS.app ({feed.plataforma})",
            titulo=title,
            resumen=summary[:350].strip(),
            url=link or f"https://rss.app/feed/{feed.id}",
            autor=author,
            fecha=pub_iso,
            metricas={
                "formato": formato,
                "plataforma": feed.plataforma,
                "tipo_fuente": "social_rssapp",
                "enfoque_id": feed.enfoque_id,
                "relevancia": 1.25,
            },
        )

    def _parse_json_entry(
        self,
        entry: Dict[str, Any],
        feed: RSSAppFeed,
        now_ts: float,
        max_age_seconds: float,
    ) -> Optional[RawItem]:
        """Extrae y valida un ítem desde un JSON Feed de RSS.app."""
        title = entry.get("title", "").strip()
        content = entry.get("content_html", "") or entry.get("content_text", "")
        link = entry.get("url", "").strip()

        if not title:
            title = clean_social_text(content)[:120]
        else:
            title = clean_social_text(title)

        if len(title) < 8:
            return None

        # Fecha de publicación
        date_pub = entry.get("date_published", "")
        pub_iso = date_pub or datetime.now(timezone.utc).isoformat()

        if feed.plataforma == "TikTok":
            formato = "video_corto"
        elif feed.plataforma == "Twitter/X":
            formato = "hilo"
        elif feed.plataforma == "LinkedIn":
            formato = "carousel"
        else:
            formato = "articulo"

        author_data = entry.get("author", {})
        author = author_data.get("name", feed.nombre) if isinstance(author_data, dict) else str(author_data)
        item_id = hashlib.sha256(f"rssapp:{feed.id}:{link or title}".encode()).hexdigest()[:16]

        return RawItem(
            id=item_id,
            fuente=f"RSS.app ({feed.plataforma})",
            titulo=title,
            resumen=content[:350].strip(),
            url=link or f"https://rss.app/feed/{feed.id}",
            autor=author or "RSS.app Creador",
            fecha=pub_iso,
            metricas={
                "formato": formato,
                "plataforma": feed.plataforma,
                "tipo_fuente": "social_rssapp",
                "enfoque_id": feed.enfoque_id,
                "relevancia": 1.25,
            },
        )
