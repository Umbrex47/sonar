"""Módulo base para las fuentes de ingesta de contenido en Radar30X.

Define el contrato de datos normalizado (RawItem) y la interfaz abstracta (BaseSource)
que deben implementar todos los ingestores (Hacker News, YouTube, Google News, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RawItem(BaseModel):
    """Representa un ítem de contenido público recolectado de cualquier fuente."""

    id: str = Field(description="Identificador único determinista o hash canónico")
    fuente: str = Field(description="Nombre canónico de la fuente (p. ej. HackerNews, YouTube)")
    titulo: str = Field(description="Título original o titular de la pieza")
    resumen: str = Field(default="", description="Descripción, extracto o síntesis del contenido")
    url: str = Field(description="URL canónica pública de la pieza")
    autor: str = Field(default="Desconocido", description="Autor, canal o creador público")
    fecha: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Fecha de publicación en formato ISO 8601",
    )
    metricas: Dict[str, Any] = Field(
        default_factory=dict,
        description="Métricas públicas cuantitativas (vistas, puntos, estrellas, comentarios, etc.)",
    )

    def get_metric(self, key: str, default: float = 0.0) -> float:
        """Obtiene una métrica numérica con valor por defecto."""
        val = self.metricas.get(key, default)
        try:
            return float(val)
        except (ValueError, TypeError):
            return default


class BaseSource(ABC):
    """Interfaz abstracta que debe implementar cada adaptador de fuente."""

    name: str = "base"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    @abstractmethod
    def fetch(self, limit: int = 50) -> List[RawItem]:
        """Recolecta y normaliza ítems públicos desde la fuente.

        Args:
            limit: Número máximo sugerido de ítems a recolectar.

        Returns:
            Lista de instancias RawItem validadas.
        """
        pass
