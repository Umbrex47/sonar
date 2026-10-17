"""Módulo de decisiones con Jev (TypeSafe AI) para Radar30X.

Jev es el 'System One Model' que toma decisiones estructuradas, type-safe y calibradas:
- No genera texto libre (evita alucinaciones por diseño).
- Clasifica fase, gancho narrativo, formato sugerido, novedad y encaje de audiencia.
- Retorna probabilidades calibradas y niveles de confianza.
"""

import logging
import os
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field
import jev

from pipeline.topics import TopicCluster

logger = logging.getLogger(__name__)


class ClusterDecision(BaseModel):
    """Esquema de salida type-safe validado por Jev."""

    fase: Literal["naciendo", "en_crecimiento", "saturado"] = Field(
        description="Fase del ciclo de vida de la tendencia según la dispersión y velocidad"
    )
    gancho: Literal["dato_contraintuitivo", "opinion", "tutorial", "contraste", "historia"] = Field(
        description="Tipo de gancho narrativo predominante que impulsa el interés en este tema"
    )
    formato: Literal["hilo", "carousel", "video_corto", "long_form", "articulo"] = Field(
        description="Formato de contenido óptimo para consumir o distribuir este tema"
    )
    novedad: float = Field(
        ge=0.0,
        le=1.0,
        description="Probabilidad de que este tema sea una novedad emergente (< 7 días)",
    )
    encaje_audiencia: float = Field(
        ge=0.0,
        le=1.0,
        description="Probabilidad de relevancia para líderes y equipos corporativos en LatAm aprendiendo IA",
    )
    confianza: float = Field(
        ge=0.0,
        le=1.0,
        description="Nivel general de certidumbre calibrada en la decisión",
    )


@jev.fn
def _jev_classify(cluster_state: str) -> ClusterDecision:
    """Evalúa un tema emergente de inteligencia artificial a partir de sus métricas cuantitativas
    (vistas por hora, estrellas, puntos, fuentes) y ejemplos de titulares reales:

    {{ cluster_state }}
    """
    return _jev_classify.state()


def _heuristic_calibrate(cluster: TopicCluster) -> ClusterDecision:
    """Motor de decisión determinista y calibrado de respaldo cuando no se dispone de clave de API.

    Replica el comportamiento de Jev evaluando métricas cuantitativas reales:
    - Velocidad de vistas/hora y ratio de novedad.
    - Dispersión de fuentes (YouTube, GitHub, HN, Medios).
    - Palabras clave de audiencia ejecutiva / operacional LatAm.
    """
    titles_text = " ".join(cluster.titulos_muestra(5)).lower()
    m = cluster.metricas_agregadas
    fuentes = set(cluster.fuentes)
    max_vph = m.get("max_vistas_por_hora", 0.0)
    total_items = m.get("total_items", 1)
    fuentes_count = len(fuentes)

    # 1. Determinar Fase
    if fuentes_count >= 4 and total_items >= 8:
        fase: Literal["naciendo", "en_crecimiento", "saturado"] = "saturado"
        novedad = 0.40
    elif max_vph > 300 or (fuentes_count in (1, 2, 3) and total_items <= 6):
        fase = "naciendo"
        novedad = 0.88
    else:
        fase = "en_crecimiento"
        novedad = 0.75

    # 2. Determinar Formato
    if any("video_corto" in it.metricas.get("formato", "") for it in cluster.items) or max_vph > 350:
        formato: Literal["hilo", "carousel", "video_corto", "long_form", "articulo"] = "video_corto"
    elif any("carousel" in it.metricas.get("formato", "") for it in cluster.items) or "herramientas" in titles_text:
        formato = "carousel"
    elif any("GitHub" in f for f in fuentes) or "código" in titles_text:
        formato = "hilo"
    elif any("Medium" in f for f in fuentes) or "análisis" in titles_text or "por qué" in titles_text:
        formato = "articulo"
    else:
        formato = "long_form"

    # 3. Determinar Gancho
    if any(w in titles_text for w in ["por qué", "mito", "error", "versus", "vs", "reemplaz"]):
        gancho: Literal["dato_contraintuitivo", "opinion", "tutorial", "contraste", "historia"] = (
            "dato_contraintuitivo"
        )
    elif any(w in titles_text for w in ["vs", "frente", "comparativa", "superando"]):
        gancho = "contraste"
    elif any(w in titles_text for w in ["cómo", "tutorial", "paso a paso", "guía"]):
        gancho = "tutorial"
    elif any(w in titles_text for w in ["demostré", "caso", "historia", "experiencia"]):
        gancho = "historia"
    else:
        gancho = "opinion"

    # 4. Encaje con Audiencia (Líderes y Equipos en LatAm)
    latam_exec_keywords = [
        "operaciones", "banca", "fintech", "directiv", "gerente", "equipo",
        "empresa", "costo", "roi", "productividad", "agente", "latam",
        "méxico", "colombia", "automatiz", "reemplaz", "compliance", "seguridad"
    ]
    matches = sum(1 for kw in latam_exec_keywords if kw in titles_text)
    encaje = min(0.65 + (matches * 0.06), 0.96)

    # 5. Confianza Calibrada
    # Mayor número de fuentes e información = mayor confianza
    confianza = min(0.78 + (fuentes_count * 0.04) + (min(total_items, 5) * 0.02), 0.95)

    return ClusterDecision(
        fase=fase,
        gancho=gancho,
        formato=formato,
        novedad=round(novedad, 2),
        encaje_audiencia=round(encaje, 2),
        confianza=round(confianza, 2),
    )


def decide_cluster(cluster: TopicCluster) -> ClusterDecision:
    """Evalúa un cluster utilizando Jev (TypeSafe System One) o fallback calibrado.

    Args:
        cluster: Instancia de TopicCluster con métricas y títulos agrupados.

    Returns:
        ClusterDecision con validación estricta de tipos Pydantic.
    """
    has_api_key = bool(os.getenv("TYPESAFE_API_KEY", "").strip())

    if has_api_key:
        state_prompt = (
            f"Tema Canónico: {cluster.tema_canonico}\n"
            f"Fuentes ({len(cluster.fuentes)}): {', '.join(cluster.fuentes)}\n"
            f"Métricas Agregadas: {cluster.metricas_agregadas}\n"
            f"Muestra de Títulos:\n"
            + "\n".join(f"- {t}" for t in cluster.titulos_muestra(4))
        )
        try:
            decision = _jev_classify(state_prompt)
            logger.info("Jev procesó exitosamente el cluster '%s'.", cluster.tema_canonico[:30])
            return decision
        except Exception as exc:
            logger.warning(
                "Llamada a Jev falló (%s). Empleando motor calibrado determinista.",
                exc,
            )

    return _heuristic_calibrate(cluster)
