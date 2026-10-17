"""Ingestor para Newsletters y Publicaciones Especializadas de IA y Ecosistema LatAm.

Fuentes públicas vía RSS:
- The Rundown AI (https://www.therundown.ai/feed)
- Startups LatAm (https://startupslatam.com/feed/)
- Rest of World (https://restofworld.org/feed/)
- TechCrunch AI (https://techcrunch.com/category/artificial-intelligence/feed/)

100% público, compliant, sin paywall ni scraping no autorizado.
Aporta señales tempranas de inversión, casos de uso empresarial y curaduría editorial de alto nivel.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import List
import feedparser
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class NewslettersSource(BaseSource):
    """Adaptador para boletines y publicaciones clave de IA y negocios."""

    name: str = "Newsletters"
    FEEDS = [
        ("The Rundown AI", "https://www.therundown.ai/feed"),
        ("Startups LatAm", "https://startupslatam.com/feed/"),
        ("Rest of World", "https://restofworld.org/feed/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ]

    def fetch(self, limit: int = 30) -> List[RawItem]:
        """Descarga y filtra artículos recientes con relevancia para la audiencia de 30X."""
        items: List[RawItem] = []
        ai_keywords = [
            "ai", "ia", "agent", "llm", "slm", "model", "rag", "automation",
            "automatiz", "startup", "founder", "operaciones", "banca", "fintech",
            "inversion", "venture", "latam", "software", "tecnologia"
        ]

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Radar30XBot/1.0"},
            ) as client:
                for publication_name, feed_url in self.FEEDS:
                    try:
                        resp = client.get(feed_url)
                        if resp.status_code != 200:
                            logger.warning("Newsletter feed %s retornó status %d", publication_name, resp.status_code)
                            continue

                        feed = feedparser.parse(resp.content)
                        for entry in feed.entries[: limit // len(self.FEEDS) + 4]:
                            title = getattr(entry, "title", "").strip()
                            if not title:
                                continue

                            summary = getattr(entry, "summary", "").strip()
                            combined_text = f"{title} {summary}".lower()

                            # Filtrar solo piezas con relevancia a tecnología, IA o negocios
                            if not any(kw in combined_text for kw in ai_keywords):
                                continue

                            link = getattr(entry, "link", "").strip()
                            author = getattr(entry, "author", publication_name)
                            published = getattr(entry, "published", "") or datetime.now(timezone.utc).isoformat()

                            item_id = hashlib.sha256(f"nl:{link or title}".encode()).hexdigest()[:16]

                            items.append(
                                RawItem(
                                    id=item_id,
                                    fuente=f"{publication_name}",
                                    titulo=title,
                                    resumen=summary[:300].strip(),
                                    url=link,
                                    autor=author,
                                    fecha=published,
                                    metricas={
                                        "formato": "articulo",
                                        "tipo_fuente": "newsletter",
                                        "relevancia": 1.2,
                                    },
                                )
                            )
                    except Exception as sub_exc:
                        logger.warning("Error al procesar feed %s: %s", publication_name, sub_exc)
        except Exception as exc:
            logger.error("Error en NewslettersSource: %s", exc)

        logger.info("Newsletters: %d ítems recolectados.", len(items))
        return items
