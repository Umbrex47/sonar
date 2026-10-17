"""Ingestor para Hacker News utilizando la API pública de Algolia.

Endpoint: https://hn.algolia.com/api/v1/search_by_date
No requiere clave de API. Cumple 100% con términos de servicio y no realiza scraping.
"""

import hashlib
import logging
from typing import List
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class HackerNewsSource(BaseSource):
    """Adaptador para recolectar historias técnicas relevantes de IA en Hacker News."""

    name: str = "HackerNews"
    BASE_URL: str = "https://hn.algolia.com/api/v1/search_by_date"

    def fetch(self, limit: int = 50) -> List[RawItem]:
        """Consulta historias recientes y destacadas con etiquetas de IA dentro de la ventana actual."""
        import time

        items: List[RawItem] = []
        # Ventana de los últimos 14 días para asegurar actualidad estricta en 2026
        two_weeks_ago = int(time.time()) - (14 * 86400)

        queries = [
            "AI agent OR agentic",
            "LLM OR 'small language model' OR SLM",
            "local AI OR 'enterprise AI'",
        ]

        try:
            with httpx.Client(timeout=self.timeout) as client:
                for q in queries:
                    params = {
                        "query": q,
                        "tags": "story",
                        "numericFilters": f"created_at_i>{two_weeks_ago}",
                        "hitsPerPage": min(limit // len(queries) + 10, 40),
                    }
                    response = client.get(self.BASE_URL, params=params)
                    if response.status_code != 200:
                        logger.warning(
                            "HN Algolia API devolvió código %s para consulta '%s'",
                            response.status_code,
                            q,
                        )
                        continue

                    data = response.json()
                    hits = data.get("hits", [])
                    for hit in hits:
                        title = hit.get("title")
                        if not title:
                            continue

                        object_id = str(hit.get("objectID", ""))
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
                        author = hit.get("author") or "hn_user"
                        created_at = hit.get("created_at") or ""
                        points = int(hit.get("points") or 0)
                        num_comments = int(hit.get("num_comments") or 0)

                        item_id = hashlib.sha256(f"hn:{object_id}".encode()).hexdigest()[:16]

                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=title.strip(),
                                resumen=f"Historia de Hacker News con {points} puntos y {num_comments} comentarios.",
                                url=url.strip(),
                                autor=author,
                                fecha=created_at,
                                metricas={
                                    "puntos": points,
                                    "comentarios": num_comments,
                                    "interacciones_totales": points + num_comments,
                                },
                            )
                        )
        except Exception as exc:
            logger.error("Error al consultar Hacker News Algolia API: %s", exc)

        logger.info("HackerNews: %d ítems recolectados.", len(items))
        return items
