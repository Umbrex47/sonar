"""Ingestor para Reddit (subreddits clave de Inteligencia Artificial).

Permite medir señales de comunidad, discusión técnica y saturación de debate.
Soporta autenticación OAuth oficial o lectura de feeds públicos en formato JSON.
"""

from datetime import datetime, timezone
import hashlib
import logging
import os
from typing import List, Optional
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class RedditSource(BaseSource):
    """Adaptador para recopilar discusiones de r/ArtificialIntelligence y r/LocalLLaMA."""

    name: str = "Reddit"
    SUBREDDITS = ["ArtificialIntelligence", "LocalLLaMA", "ChatGPT"]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self.user_agent = os.getenv("REDDIT_USER_AGENT", "Radar30X:v0.1.0 (academic/hackathon research)")

    def fetch(self, limit: int = 30) -> List[RawItem]:
        """Obtiene las publicaciones más destacadas de los subreddits de IA."""
        items: List[RawItem] = []
        headers = {"User-Agent": self.user_agent}

        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                for sub in self.SUBREDDITS:
                    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={max(limit // len(self.SUBREDDITS), 5)}"
                    resp = client.get(url)
                    if resp.status_code != 200:
                        logger.warning("Reddit r/%s devolvió código %d", sub, resp.status_code)
                        continue

                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    for post in children:
                        post_data = post.get("data", {})
                        if post_data.get("stickied"):
                            continue  # Ignorar hilos anclados de moderación

                        title = post_data.get("title", "")
                        if not title:
                            continue

                        selftext = post_data.get("selftext", "")
                        permalink = f"https://reddit.com{post_data.get('permalink', '')}"
                        author = post_data.get("author", "redditor")
                        score = int(post_data.get("score", 0))
                        num_comments = int(post_data.get("num_comments", 0))
                        created_utc = post_data.get("created_utc", 0)
                        fecha = (
                            datetime.fromtimestamp(created_utc, timezone.utc).isoformat()
                            if created_utc
                            else datetime.now(timezone.utc).isoformat()
                        )

                        item_id = hashlib.sha256(f"reddit:{permalink}".encode()).hexdigest()[:16]

                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=title.strip(),
                                resumen=selftext[:300].strip(),
                                url=permalink,
                                autor=author,
                                fecha=fecha,
                                metricas={
                                    "puntos": score,
                                    "comentarios": num_comments,
                                    "interacciones_totales": score + num_comments,
                                },
                            )
                        )
        except Exception as exc:
            logger.error("Error al consultar Reddit: %s", exc)

        logger.info("Reddit: %d ítems recolectados.", len(items))
        return items
