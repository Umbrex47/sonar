"""Ingestor para publicaciones en Medium mediante feed RSS público.

Endpoint: https://medium.com/feed/tag/artificial-intelligence
Aporta artículos de análisis profundo sobre arquitectura, implementación y casos de uso en IA.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import List
import feedparser
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class MediumSource(BaseSource):
    """Adaptador para feeds RSS públicos de Medium sobre IA."""

    name: str = "Medium"
    FEED_URLS = [
        "https://medium.com/feed/tag/artificial-intelligence",
        "https://medium.com/feed/tag/generative-ai",
    ]

    def fetch(self, limit: int = 30) -> List[RawItem]:
        """Recolecta artículos de análisis desde feeds RSS públicos de Medium."""
        items: List[RawItem] = []
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                for feed_url in self.FEED_URLS:
                    try:
                        resp = client.get(
                            feed_url,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; Radar30XBot/1.0)"},
                        )
                        if resp.status_code != 200:
                            logger.warning("Medium feed %s retornó %d", feed_url, resp.status_code)
                            continue

                        feed = feedparser.parse(resp.content)
                        ai_keywords = [
                            "ai", "ia", "agent", "llm", "slm", "model", "rag",
                            "architecture", "enterprise", "prompt", "machine learning",
                            "deep learning", "neural", "automatiz", "datos", "data"
                        ]
                        for entry in feed.entries[: limit // len(self.FEED_URLS) + 10]:
                            title = getattr(entry, "title", "")
                            summary = getattr(entry, "summary", "")
                            combined_text = f"{title} {summary}".lower()

                            # Filtrar solo piezas con relevancia técnica / IA
                            if not any(k in combined_text for k in ai_keywords):
                                continue

                            link = getattr(entry, "link", "")
                            author = getattr(entry, "author", "Medium Writer")
                            published = getattr(entry, "published", "")

                            item_id = hashlib.sha256(f"medium:{link}".encode()).hexdigest()[:16]

                            items.append(
                                RawItem(
                                    id=item_id,
                                    fuente=self.name,
                                    titulo=title.strip(),
                                    resumen=summary[:300].strip(),
                                    url=link.strip(),
                                    autor=author,
                                    fecha=published or datetime.now(timezone.utc).isoformat(),
                                    metricas={
                                        "formato": "articulo",
                                        "profundidad": "analisis",
                                    },
                                )
                            )
                    except Exception as sub_exc:
                        logger.warning("Fallo en feed %s: %s", feed_url, sub_exc)
        except Exception as exc:
            logger.error("Error al consultar Medium RSS: %s", exc)

        logger.info("Medium: %d ítems recolectados.", len(items))
        return items
