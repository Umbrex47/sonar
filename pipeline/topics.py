"""Extracción de temas y agrupación en clusters deterministas con RapidFuzz.

Cumple con el paso 4 del pipeline:
- Agrupación rápida y reproducible con `rapidfuzz.fuzz.token_set_ratio >= 75`
- Extracción de tema canónico representativo
- Consolidación de métricas multi-fuente y velocidad temporal
"""

from datetime import datetime, timezone
import hashlib
import logging
import re
from typing import Any, Dict, List, Set
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from sources.base import RawItem

logger = logging.getLogger(__name__)


class TopicCluster(BaseModel):
    """Representa un grupo consolidado de piezas sobre un mismo tema o tendencia."""

    cluster_id: str
    tema_canonico: str
    items: List[RawItem] = Field(default_factory=list)
    fuentes: List[str] = Field(default_factory=list)
    total_menciones: int = 1
    metricas_agregadas: Dict[str, Any] = Field(default_factory=dict)

    def titulos_muestra(self, n: int = 4) -> List[str]:
        """Retorna hasta n títulos representativos del cluster."""
        return [item.titulo for item in self.items[:n]]

    def urls_evidencia(self, n: int = 3) -> List[str]:
        """Retorna URLs canónicas para respaldar y trazar el hallazgo."""
        return [item.url for item in self.items[:n]]


def clean_topic_phrase(title: str) -> str:
    """Limpia ruido de titulares para obtener una frase-tema más canónica."""
    # Remover patrones de YouTube tipo [Tutorial], (2026), #Shorts, etc.
    cleaned = re.sub(r"\[.*?\]|\(.*?\)|#\w+", "", title)
    # Remover prefijos comunes como 'Show HN:', 'Ask HN:', 'Herramienta:'
    cleaned = re.sub(r"^(Show HN:|Ask HN:|Herramienta:|HN:|Notice:)\s*", "", cleaned, flags=re.I)
    # Remover puntuación excedente
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) > 8 else title.strip()


def cluster_items(
    items: List[RawItem],
    similarity_threshold: float = 75.0,
) -> List[TopicCluster]:
    """Agrupa ítems en clusters usando RapidFuzz token_set_ratio.

    Args:
        items: Lista de RawItem deduplicados.
        similarity_threshold: Umbral porcentual de token_set_ratio (75 por defecto).

    Returns:
        Lista de TopicClusters ordenados por número de ítems y tracción.
    """
    clusters: List[TopicCluster] = []

    for item in items:
        topic_phrase = clean_topic_phrase(item.titulo)
        matched_cluster: TopicCluster = None

        for c in clusters:
            score = fuzz.token_set_ratio(topic_phrase.lower(), c.tema_canonico.lower())
            if score >= similarity_threshold:
                matched_cluster = c
                break

        if matched_cluster:
            matched_cluster.items.append(item)
            if item.fuente not in matched_cluster.fuentes:
                matched_cluster.fuentes.append(item.fuente)
            matched_cluster.total_menciones += 1
        else:
            cid = hashlib.sha256(f"cluster:{topic_phrase}".encode()).hexdigest()[:12]
            new_cluster = TopicCluster(
                cluster_id=cid,
                tema_canonico=topic_phrase,
                items=[item],
                fuentes=[item.fuente],
                total_menciones=1,
            )
            clusters.append(new_cluster)

    # Calcular métricas agregadas por cluster
    for c in clusters:
        total_puntos = sum(it.get_metric("puntos") for it in c.items)
        total_vistas = sum(it.get_metric("vistas") for it in c.items)
        total_likes = sum(it.get_metric("likes") for it in c.items)
        total_comentarios = sum(it.get_metric("comentarios") for it in c.items)
        max_vph = max((it.get_metric("vistas_por_hora") for it in c.items), default=0.0)

        # Multi-fuente: diversidad de señales independientes
        fuentes_unicas = len(set(c.fuentes))

        c.metricas_agregadas = {
            "total_items": len(c.items),
            "fuentes_unicas": fuentes_unicas,
            "total_puntos": total_puntos,
            "total_vistas": total_vistas,
            "total_likes": total_likes,
            "total_comentarios": total_comentarios,
            "max_vistas_por_hora": max_vph,
        }

    # Ordenar por relevancia inicial (diversidad de fuentes y menciones)
    clusters.sort(
        key=lambda cl: (
            cl.metricas_agregadas.get("fuentes_unicas", 1) * 2
            + cl.total_menciones
            + (cl.metricas_agregadas.get("max_vistas_por_hora", 0) / 100.0)
        ),
        reverse=True,
    )

    logger.info("Agrupamiento finalizado: %d clusters generados a partir de %d ítems.", len(clusters), len(items))
    return clusters
