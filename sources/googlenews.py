"""Ingestor para Google News vía RSS público.

Endpoint: news.google.com/rss/search?q=...
Provee señal de actualidad en español y foco regional para Latinoamérica.
100% público, compliant y sin scraping de endpoints privados.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import List
import feedparser
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class GoogleNewsSource(BaseSource):
    """Adaptador para el feed RSS oficial de Google News en español."""

    name: str = "GoogleNews"
    RSS_URL: str = (
        "https://news.google.com/rss/search?q=(inteligencia+artificial+OR+IA)+empresas+when:7d&hl=es-419&gl=MX&ceid=MX:es-419"
    )

    def fetch(self, limit: int = 40) -> List[RawItem]:
        """Descarga y procesa el feed RSS de Google News."""
        items: List[RawItem] = []
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(
                    self.RSS_URL,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; Radar30XBot/1.0)"},
                )
                if resp.status_code != 200:
                    logger.warning("Google News RSS returned status %d", resp.status_code)
                    return items

                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:limit]:
                    title = getattr(entry, "title", "")
                    if not title:
                        continue

                    link = getattr(entry, "link", "")
                    summary = getattr(entry, "summary", "")
                    published = getattr(entry, "published", "")
                    source_info = getattr(entry, "source", {})
                    author = (
                        source_info.get("title")
                        if isinstance(source_info, dict)
                        else "Google News Fuente"
                    )

                    item_id = hashlib.sha256(f"gn:{link or title}".encode()).hexdigest()[:16]

                    items.append(
                        RawItem(
                            id=item_id,
                            fuente=self.name,
                            titulo=title.strip(),
                            resumen=summary[:300].strip(),
                            url=link.strip(),
                            autor=author or "Google News",
                            fecha=published or datetime.now(timezone.utc).isoformat(),
                            metricas={
                                "relevancia": 1.0,
                                "es_noticia": 1,
                            },
                        )
                    )
        except Exception as exc:
            logger.error("Error al consultar Google News RSS: %s", exc)

        logger.info("GoogleNews: %d ítems recolectados.", len(items))
        return items
