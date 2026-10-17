"""Ingestor para YouTube Data API v3.

Fuente fundamental para detectar señales cuantitativas de FORMATO (vídeo corto vs long form)
y velocidad de tracción (vistas por hora).
"""

from datetime import datetime, timezone
import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class YouTubeSource(BaseSource):
    """Adaptador para YouTube Data API v3 con cálculo de vistas/hora y detección de formato."""

    name: str = "YouTube"
    SEARCH_URL: str = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_URL: str = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0) -> None:
        super().__init__(timeout=timeout)
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")

    def _parse_iso_duration_seconds(self, duration_iso: str) -> int:
        """Convierte duraciones ISO 8601 (p. ej. PT2M15S) a segundos."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_iso)
        if not match:
            return 0
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        return h * 3600 + m * 60 + s

    def _calculate_views_per_hour(self, views: int, published_at_str: str) -> float:
        """Calcula el ratio de vistas por hora transcurrida desde la publicación."""
        try:
            pub_date = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_elapsed = max((now - pub_date).total_seconds() / 3600.0, 0.5)
            return round(views / hours_elapsed, 2)
        except Exception:
            return float(views)

    def fetch(self, limit: int = 40) -> List[RawItem]:
        """Consulta videos recientes sobre IA con la API oficial de YouTube."""
        if not self.api_key:
            logger.warning(
                "YOUTUBE_API_KEY no configurada. Utilizando modo simulado representativo de YouTube."
            )
            return self._mock_fallback()

        items: List[RawItem] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # 1. Search videos recientes sobre IA
                search_params = {
                    "part": "snippet",
                    "q": "inteligencia artificial IA novedades",
                    "type": "video",
                    "order": "date",
                    "maxResults": min(limit, 50),
                    "key": self.api_key,
                }
                search_res = client.get(self.SEARCH_URL, params=search_params)
                if search_res.status_code != 200:
                    logger.warning(
                        "YouTube Search API error %d: %s",
                        search_res.status_code,
                        search_res.text[:200],
                    )
                    return self._mock_fallback()

                search_data = search_res.json()
                video_ids = [
                    item["id"]["videoId"]
                    for item in search_data.get("items", [])
                    if "videoId" in item.get("id", {})
                ]

                if not video_ids:
                    return items

                # 2. Obtener métricas detalladas (viewCount, likeCount, contentDetails)
                video_params = {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": self.api_key,
                }
                videos_res = client.get(self.VIDEOS_URL, params=video_params)
                if videos_res.status_code != 200:
                    logger.warning("YouTube Videos API error %d", videos_res.status_code)
                    return self._mock_fallback()

                videos_data = videos_res.json()
                for vid in videos_data.get("items", []):
                    vid_id = vid.get("id")
                    snippet = vid.get("snippet", {})
                    stats = vid.get("statistics", {})
                    content_details = vid.get("contentDetails", {})

                    title = snippet.get("title", "")
                    description = snippet.get("description", "")
                    author = snippet.get("channelTitle", "Canal YouTube")
                    pub_date = snippet.get("publishedAt", "")

                    views = int(stats.get("viewCount", 0))
                    likes = int(stats.get("likeCount", 0))
                    comments = int(stats.get("commentCount", 0))

                    duration_sec = self._parse_iso_duration_seconds(
                        content_details.get("duration", "")
                    )
                    is_short = duration_sec <= 60 or "#shorts" in title.lower()
                    formato = "video_corto" if is_short else "long_form"
                    vph = self._calculate_views_per_hour(views, pub_date)

                    item_id = hashlib.sha256(f"yt:{vid_id}".encode()).hexdigest()[:16]
                    url = f"https://www.youtube.com/watch?v={vid_id}"

                    items.append(
                        RawItem(
                            id=item_id,
                            fuente=self.name,
                            titulo=title.strip(),
                            resumen=description[:300].strip(),
                            url=url,
                            autor=author,
                            fecha=pub_date,
                            metricas={
                                "vistas": views,
                                "likes": likes,
                                "comentarios": comments,
                                "vistas_por_hora": vph,
                                "duracion_segundos": duration_sec,
                                "formato": formato,
                            },
                        )
                    )
        except Exception as exc:
            logger.error("Error en YouTubeSource: %s", exc)
            return self._mock_fallback()

        logger.info("YouTube: %d ítems recolectados con la API oficial.", len(items))
        return items

    def _mock_fallback(self) -> List[RawItem]:
        """Datos de respaldo representativos cuando no se cuenta con clave API en el hackathon."""
        now = datetime.now(timezone.utc).isoformat()
        samples = [
            (
                "Agentes de IA con memoria persistente en 60 segundos",
                "Tutorial ultra-rápido demostrando cómo conectar bases vectoriales locales a agentes para empresas.",
                "DotCSV",
                42300,
                3800,
                320,
                "video_corto",
                480.5,
            ),
            (
                "Por qué los modelos locales están superando a las APIs en tareas operativas",
                "Comparativa práctica de costos de inferencia y privacidad de datos para organizaciones de LatAm.",
                "Carlos Alarcón AI",
                18900,
                1420,
                210,
                "long_form",
                195.0,
            ),
            (
                "DeepSeek vs Claude 3.5: Cuál implementar en tu empresa este mes",
                "Análisis de costo-beneficio para directores de tecnología y gerentes de innovación.",
                "Midudev Tech",
                58200,
                4600,
                580,
                "long_form",
                610.2,
            ),
        ]
        items = []
        for title, desc, author, views, likes, comments, formato, vph in samples:
            h = hashlib.sha256(f"yt:mock:{title}".encode()).hexdigest()[:16]
            items.append(
                RawItem(
                    id=h,
                    fuente=self.name,
                    titulo=title,
                    resumen=desc,
                    url=f"https://www.youtube.com/watch?v={h}",
                    autor=author,
                    fecha=now,
                    metricas={
                        "vistas": views,
                        "likes": likes,
                        "comentarios": comments,
                        "vistas_por_hora": vph,
                        "formato": formato,
                    },
                )
            )
        return items
