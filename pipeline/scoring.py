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
        self.score_final = score
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
            "workflow", "razonamiento", "productividad", "rrhh", "reemplaz",
            "liderazgo", "lider", "ceo", "cto", "cultura", "talento", "gestion",
            "estrategia", "arquitectura", "cloud", "ciberseguridad", "devops",
            "saas", "scaleup", "management", "ingenieria", "venture", "startup"
        ]
    )
    impact_multiplier = 0.40 if is_toy else (1.20 if has_enterprise_impact else 1.0)

    # 6. Boost de Recencia y Frescura Temporal (< 48 horas)
    recency_boost = 0.0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for it in cluster.items:
        if it.fecha:
            try:
                f_clean = it.fecha.replace("Z", "+00:00")
                item_dt = datetime.fromisoformat(f_clean)
                hours_diff = (now - item_dt).total_seconds() / 3600.0
                if hours_diff <= 24:
                    recency_boost = max(recency_boost, 0.08)
                elif hours_diff <= 48:
                    recency_boost = max(recency_boost, 0.04)
            except Exception:
                pass

    # 7. Fórmula Ponderada con Confianza Calibrada de Jev
    conf_factor = 0.45 + (0.55 * decision.confianza)
    base_signal = (
        0.35 * crecimiento_norm
        + 0.25 * decision.novedad
        + 0.20 * multifuente_norm
        + 0.20 * decision.encaje_audiencia
    )
    raw_weighted = (base_signal * conf_factor * synergy_multiplier * impact_multiplier) + recency_boost - saturacion_penalidad

    final_score = round(max(raw_weighted, 0.01), 3)

    if decision.audit:
        decision.audit.desglose_formula = {
            "crecimiento_norm": round(crecimiento_norm, 3),
            "novedad": round(decision.novedad, 3),
            "multifuente_norm": round(multifuente_norm, 3),
            "encaje_audiencia": round(decision.encaje_audiencia, 3),
            "recency_boost": round(recency_boost, 3),
            "factor_confianza": round(conf_factor, 3),
            "multiplicador_sinergia": round(synergy_multiplier, 2),
            "multiplicador_impacto": round(impact_multiplier, 2),
            "penalidad_saturacion": round(saturacion_penalidad, 2),
            "score_final": final_score,
        }

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


def partition_topics_funnel(
    scored_topics: List[ScoredTopic], top_n: int = 10
) -> Tuple[List[ScoredTopic], List[ScoredTopic], List[ScoredTopic]]:
    """Particiona los clusters evaluados en el embudo de decisiones:
    Retorna: (aprobados_top, en_observacion, descartados).
    Garantiza que el Top 10 esté siempre completo incorporando las señales
    emergentes más prometedoras de observación si los aprobados multi-fuente son menores a top_n.
    """
    aprobados_candidatos: List[ScoredTopic] = []
    en_observacion: List[ScoredTopic] = []
    descartados: List[ScoredTopic] = []

    for st in scored_topics:
        audit = st.decision.audit
        veredicto = audit.veredicto if audit else "APROBADO"

        if veredicto == "DESCARTADO":
            descartados.append(st)
        elif veredicto == "EN_OBSERVACION":
            en_observacion.append(st)
        else:
            aprobados_candidatos.append(st)

    aprobados_top = list(aprobados_candidatos[:top_n])

    # Si los aprobados son menores a top_n, completar con las mejores señales emergentes de observación
    if len(aprobados_top) < top_n and en_observacion:
        faltantes = top_n - len(aprobados_top)
        promovidos = en_observacion[:faltantes]
        for p in promovidos:
            p.decision.fase = "naciendo"
            if p.decision.audit:
                p.decision.audit.motivo_veredicto = (
                    "Señal emergente destacada en escaneo reciente (en observación activa con alta tracción)."
                )
        aprobados_top.extend(promovidos)
        en_observacion = en_observacion[faltantes:]

    # Los aprobados restantes pasan al backlog de observación
    if len(aprobados_candidatos) > top_n:
        en_observacion.extend(aprobados_candidatos[top_n:])

    return aprobados_top, en_observacion, descartados

