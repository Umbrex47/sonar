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
    """Extrae la frase-tema canónica identificando conceptos de tendencia de IA en 2026."""
    text = f"{title} {summary}".lower()

    # Mapeo a conceptos canónicos clave de tendencias de IA en 2026
    if any(k in text for k in ["rpa", "workflow", "operations", "operacion", "conciliaci", "prospecc"]) and any(k in text for k in ["agent", "agente", "ia", "ai", "automatiz"]):
        return "Agentes Autónomos en Operaciones y Reemplazo de RPA"

    if any(k in text for k in ["sandbox", "airlock", "jailbreak", "guardrail", "netlumi", "agent37", "vulnerab"]) and any(k in text for k in ["agent", "agente", "ia", "ai", "security", "seguridad"]):
        return "Sandboxing, Seguridad y Trazabilidad de Agentes de IA"

    if any(k in text for k in ["claude code", "codex", "merlin", "coding agent", "shadowclone", "cursor", "replit", "rdst"]):
        return "Coding Agents y Automatización del Desarrollo de Software"

    if any(k in text for k in ["qwen", "deepseek", "slm", "small language", "open-source", "open-weight", "nemotron", "sam3", "drama-3", "embeddinggemma"]):
        return "Modelos de Razonamiento Open Source y SLMs Especializados"

    if any(k in text for k in ["empleo", "mexicanas", "méxico", 'mexico', "colombia", "chile", "latam", "bradesco", "talento"]) and any(k in text for k in ["empresa", "adopción", "adopcion", "ia", "inteligencia artificial"]):
        return "Adopción Corporativa de IA y Transformación Laboral en LatAm"

    if any(k in text for k in ["compliance", "auditor", "regulac", "sesgo", "normativ"]) and any(k in text for k in ["ia", "ai", "legal", "rrhh", "recursos humanos"]):
        return "Gobernanza, Compliance y Auditoría de IA en Empresas"

    # Polémicas de Labs: Anthropic, OpenAI, despidos de seguridad, demandas, rupturas
    if any(k in text for k in ["anthropic", "openai", "sam altman", "dario amodei", "fired safety", "whistleblower", "lawsuit", "demandas", "copyright", "ruptura"]) and any(k in text for k in ["ai", "ia", "safety", "seguridad", "replit", "controversia", "polémica", "polemica"]):
        return "Polémicas y Gobernanza de Grandes Labs (OpenAI / Anthropic)"

    # Benchmarks & Model Race
    if any(k in text for k in ["benchmark", "swe-bench", "evals", "evaluaci", "reasoning benchmark", "o3", "deepseek v3", "math benchmark"]) and any(k in text for k in ["ai", "ia", "model", "modelo", "score", "rendimiento", "inferencia"]):
        return "Benchmarks y Carrera de Modelos de Razonamiento (o3 vs Claude vs DeepSeek)"

    # Desarrollo Personal como CEO & Liderazgo Tecnológico
    if any(k in text for k in ["ceo", "liderazgo", "leadership", "founder", "directivo", "director"]) and any(k in text for k in ["desarrollo personal", "productividad", "toma de decisiones", "cultura", "mental model", "gestión", "gestion", "mindset"]):
        return "Desarrollo Personal de CEO y Liderazgo Estratégico con IA"

    # Oportunidades de Negocio y ROI
    if any(k in text for k in ["roi", "retorno de inversión", "retorno de inversion", "oportunidades", "oportunidad", "monetizaci", "reducción de costos", "reduccion de costos"]) and any(k in text for k in ["empresa", "negocio", "ia", "ai", "banca", "fintech"]):
        return "Oportunidades de Negocio y Retorno de Inversión (ROI) en IA"

    if any(k in text for k in ["memoria", "memory", "persist", "vector", "local ai", "base local"]) and any(k in text for k in ["agent", "agente", "ia"]):
        return "Agentes de IA con Memoria Persistente y Bases Locales"

    if any(k in text for k in ["pika", "video studio", "generative video", "watermelon", "audio visual", "musica ia"]):
        return "Generación Multimodal y Agentes Audiovisuales"

    # Limpieza estándar si es un tema nuevo o especializado
    cleaned = re.sub(r"\[.*?\]|\(.*?\)|#\w+", "", title)
    cleaned = re.sub(r"^(Show HN:|Ask HN:|Herramienta:|HN:|Notice:)\s*", "", cleaned, flags=re.I)
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
