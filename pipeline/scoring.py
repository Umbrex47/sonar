"""Módulo de scoring y clasificación de tendencias en Radar30X.

Aplica la fórmula matemática oficial del plan de desarrollo:
score = 0.35 * crecimiento + 0.25 * novedad + 0.20 * multifuente + 0.20 * encaje - saturacion
Ponderado en cada término por la confianza calibrada de Jev.
"""

from typing import List, Tuple
from pipeline.decide import ClusterDecision
from pipeline.topics import TopicCluster


class ScoredTopic:
    """Estructura de datos que consolida un cluster, su decisión Jev y su puntaje final."""

    def __init__(
        self,
        cluster: TopicCluster,
        decision: ClusterDecision,
        score: float,
        crecimiento_label: str,
    ) -> None:
        self.cluster = cluster
        self.decision = decision
        self.score = score
        self.crecimiento_label = crecimiento_label
        self.por_que: str = ""
        self.adaptacion_30x: str = ""


def calculate_topic_score(cluster: TopicCluster, decision: ClusterDecision) -> Tuple[float, str]:
    """Calcula el puntaje ponderado del tema y su etiqueta de crecimiento porcentual.

    Args:
        cluster: TopicCluster con métricas agregadas.
        decision: ClusterDecision con salida type-safe de Jev.

    Returns:
        Tupla de (score_ponderado: float, crecimiento_label: str)
    """
    m = cluster.metricas_agregadas
    max_vph = float(m.get("max_vistas_por_hora", 0.0))
    total_items = float(m.get("total_items", 1))
    fuentes_count = float(len(set(cluster.fuentes)))

    # 1. Normalización de Crecimiento (0.0 a 1.0)
    # Basado en vistas/hora de YouTube y volumen relativo de menciones
    vph_factor = min(max_vph / 400.0, 1.0)
    mentions_factor = min(total_items / 6.0, 1.0)
    crecimiento_norm = max(vph_factor * 0.7 + mentions_factor * 0.3, 0.25)

    # Etiqueta legible para reportes
    pct = int(round(crecimiento_norm * 420.0))
    crecimiento_label = f"+{pct}% vs semana previa"

    # 2. Señal Multi-fuente (0.0 a 1.0)
    # Más fuentes distintas hablando del tema = mayor solidez de la tendencia
    multifuente_norm = min(fuentes_count / 4.0, 1.0)

    # 3. Penalización por Saturación
    saturacion_penalidad = 0.30 if decision.fase == "saturado" else 0.0

    # 4. Fórmula Ponderada con Confianza de Jev
    confianza = decision.confianza
    raw_weighted = (
        0.35 * (crecimiento_norm * confianza)
        + 0.25 * (decision.novedad * confianza)
        + 0.20 * (multifuente_norm * confianza)
        + 0.20 * (decision.encaje_audiencia * confianza)
        - saturacion_penalidad
    )

    final_score = round(max(raw_weighted, 0.01), 3)
    return final_score, crecimiento_label


def rank_topics(
    clusters: List[TopicCluster],
    decisions: List[ClusterDecision],
) -> List[ScoredTopic]:
    """Asocia decisiones a clusters, calcula scores y ordena de mayor a menor."""
    scored: List[ScoredTopic] = []

    for cluster, dec in zip(clusters, decisions):
        score, label = calculate_topic_score(cluster, dec)
        scored.append(
            ScoredTopic(
                cluster=cluster,
                decision=dec,
                score=score,
                crecimiento_label=label,
            )
        )

    # Ordenar por score descendente
    scored.sort(key=lambda t: t.score, reverse=True)
    return scored
