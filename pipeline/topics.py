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

    # 5. Normalizar entidades tecnológicas clave para validación cruzada multi-fuente
    t_lower = f"{text} {summary}".lower()

    if any(k in t_lower for k in ["claude code", "claude 3.7", "claude 3.5 sonnet", "computer use anthropic"]):
        return "Claude Code y Automatización del Software"
    if any(k in t_lower for k in ["deepseek-r1", "deepseek r1", "deepseek v3", "deepseek-v3"]) or ("deepseek" in t_lower and any(k in t_lower for k in ["reasoning", "razonamiento", "benchmark", "cost", "costo", "inferencia"])):
        return "DeepSeek-R1 y Modelos de Razonamiento Open Source"
    if any(k in t_lower for k in ["openai o3", "openai o1", "o3-mini", "o1-mini", "reasoning model", "modelo de razonamiento"]) and any(k in t_lower for k in ["openai", "sam altman", "enterprise", "empresa"]):
        return "OpenAI o3/o1 y Modelos de Razonamiento Enterprise"
    if "graphrag" in t_lower or "graph rag" in t_lower or ("grafo" in t_lower and "rag" in t_lower):
        return "GraphRAG y Grafos de Conocimiento Empresarial"
    if any(k in t_lower for k in ["model context protocol", "protocolo mcp", "mcp server", "servidor mcp"]) or ("mcp" in t_lower and "anthropic" in t_lower):
        return "Model Context Protocol (MCP) y Conectividad de Agentes"
    if any(k in t_lower for k in ["webrtc", "voice agent", "agente de voz", "voz en tiempo real"]) and any(k in t_lower for k in ["ia", "ai", "realtime", "tiempo real", "latencia"]):
        return "Agentes de Voz en Tiempo Real y Latencia Ultrabaja"
    if any(k in t_lower for k in ["sandbox", "airlock", "guardrail", "safebox", "aislamiento"]) and any(k in t_lower for k in ["agent", "agente", "ia", "ai"]):
        return "Sandboxing, Seguridad y Aislamiento de Agentes"
    if any(k in t_lower for k in ["reemplazo rpa", "reemplazar rpa", "rpa tradicional"]) or (any(k in t_lower for k in ["operaciones", "automatización"]) and any(k in t_lower for k in ["agente autónomo", "agentes autónomos", "autonomous agents", "oficina de agentes"])):
        return "Reemplazo de RPA por Agentes Autónomos de Operaciones"
    if any(k in t_lower for k in ["slm", "small language model", "modelos pequeños", "vllm", "ollama", "inferencia local", "modelos locales"]):
        return "Modelos SLM y Eficiencia de Inferencia Local"
    if any(k in t_lower for k in ["latam", "américa latina", "latinoamérica", "mexico", "colombia"]) and any(k in t_lower for k in ["adopción", "banca", "fintech", "ia en empresas", "soberanía"]):
        return "Adopción y Soberanía de IA en Empresas de LatAm"
    if any(k in t_lower for k in ["sam altman", "dario amodei", "whistleblower", "demanda copyright", "antitrust ia", "salidas ejecutivos"]) and any(k in t_lower for k in ["openai", "anthropic", "meta", "google"]):
        return "Gobernanza y Controversias en Grandes Laboratorios de IA"
    if any(k in t_lower for k in ["swe-bench", "swebench", "benchmark de razonamiento", "evals de ia"]) and any(k in t_lower for k in ["eval", "evaluacion", "coding", "razonamiento"]):
        return "Benchmarks de Rendimiento y Evaluaciones SWE-bench"
    if any(k in t_lower for k in ["liderazgo tecnologico", "tech leadership", "engineering management", "cultura de ingenieria", "cultura ingenieria", "retencion talento tech", "gestion de equipos tech", "cto leadership"]):
        return "Liderazgo Tecnológico y Gestión de Equipos de Ingeniería"
    if any(k in t_lower for k in ["arquitectura de software", "cloud native", "microservicios", "monolito modular", "resiliencia infraestructura", "finops", "devops"]) and any(k in t_lower for k in ["arquitectura", "cloud", "infraestructura", "software", "sistema", "escalabilidad"]):
        return "Arquitectura Cloud Native, Microservicios y Resiliencia"
    if any(k in t_lower for k in ["ciberseguridad corporativa", "vulnerabilidad", "zero trust", "ransomware empresas", "seguridad cloud", "ciso"]) or ("ciberseguridad" in t_lower and any(k in t_lower for k in ["empresa", "corporativ", "amenaza", "riesgo"])):
        return "Ciberseguridad Corporativa y Gestión de Vulnerabilidades"
    if any(k in t_lower for k in ["venture capital latam", "startups latam", "ronda seed", "series a", "unit economics", "rule of 40", "scaleup latam", "inversion tech"]) or ("startup" in t_lower and any(k in t_lower for k in ["ronda", "capital", "inversion", "latam", "saas"])):
        return "Ecosistema de Startups y Venture Capital en LatAm"
    if any(k in t_lower for k in ["ceo", "liderazgo", "productividad directiva", "directores"]) and any(k in t_lower for k in ["inteligencia artificial", "ia", "estrategia"]):
        return "Liderazgo y Productividad Directiva con IA"

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
    similarity_threshold: float = 68.0,
) -> List[TopicCluster]:
    """Agrupa ítems en clusters usando RapidFuzz token_set_ratio y coincidencia de entidades.

    Args:
        items: Lista de RawItem deduplicados.
        similarity_threshold: Umbral porcentual de token_set_ratio (68 por defecto).

    Returns:
        Lista de TopicClusters ordenados por número de ítems y tracción.
    """
    clusters: List[TopicCluster] = []

    for item in items:
        topic_phrase = clean_topic_phrase(item.titulo, item.resumen)
        matched_cluster: TopicCluster = None

        for c in clusters:
            if topic_phrase.lower() == c.tema_canonico.lower():
                matched_cluster = c
                break
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
