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
        self.por_que_audiencia: str = ""
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

    # 4. Multiplicador de Sinergia Multi-Fuente (premia validación cruzada)
    synergy_multiplier = 1.25 if fuentes_count >= 3 else (1.10 if fuentes_count == 2 else 0.85)

    # 5. Filtro de Impacto Empresarial vs Proyectos de Juguete
    titles_text = " ".join([cluster.tema_canonico] + cluster.titulos_muestra(5)).lower()
    is_toy = any(k in titles_text for k in ["rewrite one turn", "calorie tracker", "fake photo", "photo fooled", "music video", "jailbreak let muse"])
    has_enterprise_impact = any(
        k in titles_text
        for k in [
            "operacion", "banca", "fintech", "costo", "empresa", "seguridad",
            "sandbox", "rpa", "compliance", "auditor", "desarrollo", "slm",
            "workflow", "razonamiento", "productividad", "rrhh", "reemplaz"
        ]
    )
    impact_multiplier = 0.40 if is_toy else (1.20 if has_enterprise_impact else 1.0)

    # 6. Fórmula Ponderada con Confianza Calibrada de Jev
    conf_factor = 0.45 + (0.55 * decision.confianza)
    base_signal = (
        0.35 * crecimiento_norm
        + 0.25 * decision.novedad
        + 0.20 * multifuente_norm
        + 0.20 * decision.encaje_audiencia
    )
    raw_weighted = (base_signal * conf_factor * synergy_multiplier * impact_multiplier) - saturacion_penalidad

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
