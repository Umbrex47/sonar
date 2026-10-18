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


def clean_topic_phrase(title: str, summary: str = "") -> str:
    """Extrae y normaliza de forma dinámica la frase-tema representativa de un ítem,
    eliminando ruido, prefijos y sufijos de canales, pero preservando la especificidad del tema."""
    if not title:
        return "Tendencia de IA Emergente"

    text = title.strip()

    # 1. Eliminar etiquetas entre corchetes, paréntesis comunes o hashtags
    text = re.sub(r"\[.*?\]|\(.*?\)|#\w+", "", text)

    # 2. Eliminar prefijos de publicación o agregadores comunes
    text = re.sub(
        r"^(Show HN:|Ask HN:|Herramienta:|HN:|Notice:|Breaking:|Video:|Podcast:|Tutorial:|Guía:|Exclusiva:|URGENTE:)\s*",
        "",
        text,
        flags=re.I,
    )

    # 3. Eliminar sufijos típicos de canales de YouTube, medios o plataformas
    text = re.sub(
        r"\s*(\||\-)\s*(YouTube|DotCSV|Fireship|Matt Wolfe|Lex Fridman|TechCrunch|The Verge|El Economista|Infobae|Forbes|X|Medium|GitHub|Reddit|HN).*$",
        "",
        text,
        flags=re.I,
    )

    # 4. Eliminar clickbait / frases vacías iniciales
    text = re.sub(
        r"^(Por qué|Why|Cómo|How to|Here is why|The truth about|Todo sobre|Lo que nadie te dice de)\s+",
        "",
        text,
        flags=re.I,
    )

    # 5. Normalizar entidades tecnológicas muy específicas reconocidas (sin absorber temas generales)
    t_lower = f"{text} {summary}".lower()
    if "claude code" in t_lower:
        return "Claude Code y Automatización del Software"
    if "graphrag" in t_lower or "graph rag" in t_lower:
        return "GraphRAG y Grafos de Conocimiento Empresarial"
    if "deepseek-r1" in t_lower or "deepseek r1" in t_lower:
        return "DeepSeek-R1 y Modelos de Razonamiento Open Source"
    if any(k in t_lower for k in ["webrtc", "voice agent", "agente de voz"]) and any(k in t_lower for k in ["ia", "ai", "realtime", "tiempo real"]):
        return "Agentes de Voz en Tiempo Real y Latencia Ultrabaja"
    if any(k in t_lower for k in ["sandbox", "airlock", "guardrail"]) and any(k in t_lower for k in ["agent", "agente"]):
        return "Sandboxing, Seguridad y Aislamiento de Agentes"

    # 6. Limpieza de puntuación y espacios residuales
    text = re.sub(r"^[–—:\-\s]+|[–—:\-\s]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Si quedó muy corto o vacío, volver al título original sin tags
    if len(text) < 8:
        clean_raw = re.sub(r"[\[\]#]", "", title).strip()
        return clean_raw if len(clean_raw) >= 5 else title.strip()

    # Normalizar capitalización si está todo en mayúsculas
    if text.isupper():
        text = text.title()

    return text


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
        topic_phrase = clean_topic_phrase(item.titulo, item.resumen)
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
