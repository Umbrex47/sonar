"""Ingestor para Hugging Face Hub (Trending Models y Daily Papers).

Endpoints públicos oficiales:
- https://huggingface.co/api/trending?limit=25&type=model
- https://huggingface.co/api/daily_papers
100% público, compliant, sin autenticación obligatoria y sin scraping.
Permite detectar qué modelos open-weights y arquitecturas están explotando en adopción técnica real.
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import List
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class HuggingFaceSource(BaseSource):
    """Adaptador para el Hub de Hugging Face enfocado en modelos y papers trending."""

    name: str = "HuggingFace"
    TRENDING_MODELS_URL = "https://huggingface.co/api/trending"
    DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"

    def fetch(self, limit: int = 30) -> List[RawItem]:
        """Consulta modelos trending y los papers más votados del día."""
        items: List[RawItem] = []
        now = datetime.now(timezone.utc).isoformat()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # 1. Modelos trending (HF impone un límite máximo de 20 por petición)
                params = {"limit": min(limit, 20), "type": "model"}
                resp_models = client.get(self.TRENDING_MODELS_URL, params=params)
                if resp_models.status_code == 200:
                    data = resp_models.json()
                    trending = data.get("recentlyTrending", [])
                    for entry in trending[: limit // 2]:
                        repo_data = entry.get("repoData", {})
                        repo_id = repo_data.get("id", "")
                        if not repo_id:
                            continue

                        likes = int(repo_data.get("likes", 0))
                        downloads = int(repo_data.get("downloads", 0))
                        author = repo_id.split("/")[0] if "/" in repo_id else "Comunidad HF"
                        url = f"https://huggingface.co/{repo_id}"
                        item_id = hashlib.sha256(f"hf:model:{repo_id}".encode()).hexdigest()[:16]

                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=f"Modelo Open Source: {repo_id}",
                                resumen=f"Modelo en tendencia en Hugging Face con {downloads:,} descargas y {likes:,} likes.",
                                url=url,
                                autor=author,
                                fecha=now,
                                metricas={
                                    "descargas": downloads,
                                    "likes": likes,
                                    "interacciones_totales": likes + (downloads // 50),
                                    "formato": "hilo",
                                },
                            )
                        )

                # 2. Daily Papers más votados
                resp_papers = client.get(self.DAILY_PAPERS_URL)
                if resp_papers.status_code == 200:
                    papers = resp_papers.json()
                    for p in papers[: limit // 2]:
                        paper_info = p.get("paper", {})
                        title = paper_info.get("title", "")
                        if not title:
                            continue

                        paper_id = paper_info.get("id", "")
                        summary = paper_info.get("summary", "")
                        upvotes = int(paper_info.get("upvotes", 0))
                        authors = paper_info.get("authors", [])
                        author_name = authors[0].get("name") if authors else "Investigadores IA"
                        url = f"https://huggingface.co/papers/{paper_id}"
                        item_id = hashlib.sha256(f"hf:paper:{paper_id}".encode()).hexdigest()[:16]

                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=f"Paper: {title}",
                                resumen=summary[:300].strip(),
                                url=url,
                                autor=author_name,
                                fecha=now,
                                metricas={
                                    "upvotes": upvotes,
                                    "interacciones_totales": upvotes * 5,
                                    "formato": "articulo",
                                },
                            )
                        )
        except Exception as exc:
            logger.error("Error al consultar Hugging Face API: %s", exc)

        logger.info("HuggingFace: %d ítems recolectados.", len(items))
        return items
