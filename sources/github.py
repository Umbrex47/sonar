"""Ingestor para repositorios emergentes en GitHub Search API.

Endpoint: https://api.github.com/search/repositories?q=topic:ai...&sort=stars
Permite descubrir nuevas herramientas de código abierto, frameworks de agentes y librerías
que están siendo adoptadas velozmente por desarrolladores.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
from typing import List, Optional
import httpx

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class GitHubSource(BaseSource):
    """Adaptador para GitHub Search API enfocado en proyectos de IA con alto crecimiento."""

    name: str = "GitHub"
    SEARCH_URL = "https://api.github.com/search/repositories"

    def __init__(self, token: Optional[str] = None, timeout: float = 15.0) -> None:
        super().__init__(timeout=timeout)
        self.token = token or os.getenv("GITHUB_TOKEN", "")

    def fetch(self, limit: int = 30) -> List[RawItem]:
        """Busca repositorios creados o con actividad reciente sobre IA y agentes."""
        items: List[RawItem] = []
        # Ventana de los últimos 14 días
        two_weeks_ago = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
        queries = [
            f"topic:ai created:>{two_weeks_ago} sort:stars",
            f"topic:developer-tools created:>{two_weeks_ago} sort:stars",
            f"topic:devops created:>{two_weeks_ago} sort:stars",
        ]

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Radar30X-Bot",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                for q in queries:
                    params = {"q": q, "per_page": min(limit // len(queries) + 5, 30)}
                    resp = client.get(self.SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        logger.warning(
                            "GitHub API devolvió código %d: %s",
                            resp.status_code,
                            resp.text[:150],
                        )
                        continue

                    data = resp.json()
                    repos = data.get("items", [])
                    for repo in repos:
                        name = repo.get("full_name", "")
                        desc = repo.get("description") or "Repositorio de IA en GitHub"
                        html_url = repo.get("html_url", "")
                        stars = int(repo.get("stargazers_count", 0))
                        forks = int(repo.get("forks_count", 0))
                        created_at = repo.get("created_at", "")
                        owner = repo.get("owner", {}).get("login", "github_user")

                        item_id = hashlib.sha256(f"gh:{html_url}".encode()).hexdigest()[:16]

                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=f"Herramienta: {name}",
                                resumen=f"{desc} (⭐ {stars} estrellas, {forks} forks)",
                                url=html_url,
                                autor=owner,
                                fecha=created_at,
                                metricas={
                                    "estrellas": stars,
                                    "forks": forks,
                                    "interacciones_totales": stars + forks,
                                },
                            )
                        )
        except Exception as exc:
            logger.error("Error al consultar GitHub API: %s", exc)

        logger.info("GitHub: %d ítems recolectados.", len(items))
        return items

    def fetch_window(self, start_date: str, end_date: str, limit: int = 25) -> List[RawItem]:
        """Busca repositorios creados dentro de una ventana de fechas específica para backfill."""
        items: List[RawItem] = []
        queries = [
            f"topic:ai created:{start_date}..{end_date} sort:stars",
            f"topic:llm created:{start_date}..{end_date} sort:stars",
        ]
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Radar30X-Bot",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                for q in queries:
                    params = {"q": q, "per_page": min(limit // len(queries) + 5, 20)}
                    resp = client.get(self.SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        continue
                    repos = resp.json().get("items", [])
                    for repo in repos:
                        name = repo.get("full_name", "")
                        desc = repo.get("description") or "Repositorio de IA en GitHub"
                        html_url = repo.get("html_url", "")
                        stars = int(repo.get("stargazers_count", 0))
                        forks = int(repo.get("forks_count", 0))
                        created_at = repo.get("created_at", "")
                        owner = repo.get("owner", {}).get("login", "github_user")
                        item_id = hashlib.sha256(f"gh:{html_url}".encode()).hexdigest()[:16]
                        items.append(
                            RawItem(
                                id=item_id,
                                fuente=self.name,
                                titulo=f"Herramienta: {name}",
                                resumen=f"{desc} (⭐ {stars} estrellas, {forks} forks)",
                                url=html_url,
                                autor=owner,
                                fecha=created_at,
                                metricas={
                                    "estrellas": stars,
                                    "forks": forks,
                                    "interacciones_totales": stars + forks,
                                },
                            )
                        )
        except Exception as exc:
            logger.error("Error al consultar backfill de GitHub: %s", exc)
        return items

