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

import html
import re
import urllib.parse
from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class GoogleNewsSource(BaseSource):
    """Adaptador para el feed RSS oficial de Google News en español con soporte multi-enfoque."""

    name: str = "GoogleNews"
    BASE_URL: str = "https://news.google.com/rss/search"

    def _get_queries(self) -> List[str]:
        """Genera consultas para Google News con rotación dinámica basada en enfoques activos."""
        import random
        base_queries: List[str] = [
            "(inteligencia artificial OR IA) (OpenAI OR Anthropic OR DeepSeek OR Gemini) when:3d",
            "(liderazgo tecnologico OR CTO OR CEO tech) (equipos OR talento OR cultura) when:5d",
            "(arquitectura software OR cloud OR ciberseguridad OR startups) (empresas OR LatAm) when:5d",
        ]
        focus_queries: List[str] = []
        try:
            from pipeline.focuses import load_focuses
            focuses = load_focuses()
            active_f = [f for f in focuses if f.activo]
            for f in active_f:
                if f.keywords:
                    kw_sample = random.sample(f.keywords, min(2, len(f.keywords)))
                    kw_clause = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in kw_sample)
                    q = f"({kw_clause}) (tech OR liderazgo OR empresas OR IA) when:5d"
                    if q not in focus_queries:
                        focus_queries.append(q)
        except Exception as e:
            logger.debug("No se pudieron cargar enfoques para Google News: %s", e)

        # Rotar y seleccionar consultas para este escaneo
        random.shuffle(focus_queries)
        selected = base_queries[:2] + focus_queries[:3]
        return selected

    def fetch(self, limit: int = 50) -> List[RawItem]:
        """Descarga y procesa feeds RSS de Google News a través de múltiples enfoques temáticos."""
        items: List[RawItem] = []
        seen_urls = set()
        queries = self._get_queries()

        per_query_limit = max(8, limit // max(1, len(queries)))

        from pipeline.scraper import HybridScraper
        scraper = HybridScraper()

        for q in queries:
            try:
                encoded = urllib.parse.quote(q)
                url = f"{self.BASE_URL}?q={encoded}&hl=es-419&gl=MX&ceid=MX:es-419"
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    )
                    if resp.status_code != 200:
                        continue

                    feed = feedparser.parse(resp.content)
                    for entry in feed.entries[:per_query_limit]:
                        title = getattr(entry, "title", "").strip()
                        if not title:
                            continue

                        link = getattr(entry, "link", "").strip()
                        if not link or link in seen_urls:
                            continue

                        summary = getattr(entry, "summary", "")
                        clean_summary = re.sub(r"<[^>]+>", " ", summary)
                        clean_summary = html.unescape(clean_summary).strip()

                        published = getattr(entry, "published", "")
                        source_info = getattr(entry, "source", {})
                        author = (
                            source_info.get("title")
                            if isinstance(source_info, dict)
                            else "Google News"
                        )

                        # Resolver a URL canónica original para los primeros ítems clave
                        final_url = link
                        if "news.google.com" in link and len(items) < 15:
                            resolved = scraper.resolve_google_news_url(link, timeout=4.0)
                            if resolved:
                                final_url = resolved

                        seen_urls.add(final_url)
                        item_id = hashlib.sha256(f"gn:{final_url or title}".encode()).hexdigest()[:16]

                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=title,
                                resumen=clean_summary[:350],
                                url=final_url,
                                autor=author or "Google News",
                                fecha=published or datetime.now(timezone.utc).isoformat(),
                                metricas={
                                    "relevancia": 1.0,
                                    "es_noticia": 1,
                                    "query": q,
                                },
                            )
                        )
                        if len(items) >= limit:
                            break
            except Exception as exc:
                logger.debug("Error consultando Google News con query '%s': %s", q, exc)

            if len(items) >= limit:
                break

        logger.info("GoogleNews (Scraper Híbrido): %d ítems recolectados a través de %d consultas.", len(items), len(queries))
        return items

