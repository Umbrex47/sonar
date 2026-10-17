"""Módulo de Telemetría y Playground Interactivo para JEV (TypeSafe System 1).

Permite evaluar noticias individuales en tiempo real, visualizar las 5 preguntas
ejecutivas formuladas a Jev, y simular el impacto de variaciones en métricas cuantitativas.
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from pipeline.decide import ClusterDecision, decide_cluster
from pipeline.scoring import calculate_topic_score
from pipeline.topics import TopicCluster
from sources.base import RawItem


class PlaygroundTelemetry(BaseModel):
    """Telemetría estructurada devuelta por el Playground de Jev."""

    tema: str
    fuentes: List[str]
    vistas_por_hora: float
    preguntas_jev: List[Dict[str, Any]]
    decision: ClusterDecision
    score_final: float
    crecimiento_label: str
    score_breakdown: Dict[str, Any]
    latencia_ms: float
    motor_utilizado: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def evaluate_playground_item(
    tema: str,
    fuentes: Optional[List[str]] = None,
    vistas_por_hora: float = 150.0,
    titulos_muestra: Optional[List[str]] = None,
    antiguedad_dias: int = 3,
) -> PlaygroundTelemetry:
    """Evalúa un tema individual y genera la telemetría detallada de preguntas y decisiones."""
    t0 = time.perf_counter()
    active_fuentes = fuentes or ["HackerNews", "YouTube"]
    active_titles = titulos_muestra or [tema]

    # Construir ítems representativos para el cluster
    items = []
    for idx, f in enumerate(active_fuentes):
        title = active_titles[idx % len(active_titles)]
        items.append(
            RawItem(
                id=f"play-{idx}",
                fuente=f,
                titulo=title,
                url=f"https://radar30x.internal/test/{idx}",
                metricas={
                    "vistas_por_hora": vistas_por_hora if f == "YouTube" else 0.0,
                    "formato": "video_corto" if vistas_por_hora > 300 else "articulo",
                },
            )
        )

    cluster = TopicCluster(
        cluster_id=f"play-{int(time.time())}",
        tema_canonico=tema,
        items=items,
        fuentes=active_fuentes,
        total_menciones=len(items),
        metricas_agregadas={
            "max_vistas_por_hora": vistas_por_hora,
            "total_items": len(items),
        },
    )

    # 1. Definir las 5 preguntas que se le formulan a Jev
    preguntas_jev = [
        {
            "id": "p1_fase",
            "pregunta": "¿En qué fase de adopción se encuentra esta tendencia?",
            "opciones": ["naciendo", "en_crecimiento", "saturado"],
            "proposito": "Determinar si es una oportunidad emergente temprana o si el mercado ya está saturado de copias.",
        },
        {
            "id": "p2_gancho",
            "pregunta": "¿Cuál es el gancho psicológico de mayor conversión?",
            "opciones": ["dato_contraintuitivo", "opinion", "tutorial", "contraste", "historia"],
            "proposito": "Identificar el mecanismo cognitivo para capturar la atención en los primeros 10 segundos.",
        },
        {
            "id": "p3_formato",
            "pregunta": "¿Cuál es el formato nativo ideal para distribuirlo?",
            "opciones": ["video_corto", "carousel", "hilo", "long_form", "articulo"],
            "proposito": "Recomendar si debe ser un Short/Reel, un Carrusel en LinkedIn o una Masterclass técnica.",
        },
        {
            "id": "p4_novedad",
            "pregunta": "¿Qué probabilidad existe de que sea una novedad emergente (< 7 días)?",
            "opciones": ["0.00 a 1.00 (probabilidad calibrada)"],
            "proposito": "Filtrar refritos o herramientas del año anterior que reviven artificialmente.",
        },
        {
            "id": "p5_encaje",
            "pregunta": "¿Qué nivel de relevancia tiene para líderes y directores en LatAm?",
            "opciones": ["0.00 a 1.00 (afinidad de audiencia)"],
            "proposito": "Evaluar si aborda costos, ROI, operaciones, seguridad o personas en empresas de la región.",
        },
    ]

    # 2. Tomar decisión con Jev
    decision = decide_cluster(cluster)
    latencia_ms = round((time.perf_counter() - t0) * 1000, 1)

    # 3. Calcular desglose de scoring
    final_score, crecimiento_label = calculate_topic_score(cluster, decision)

    fuentes_count = len(active_fuentes)
    synergy_multiplier = 1.25 if fuentes_count >= 3 else (1.10 if fuentes_count == 2 else 0.85)

    titles_text = " ".join([cluster.tema_canonico] + cluster.titulos_muestra(5)).lower()
    is_toy = any(k in titles_text for k in ["rewrite one turn", "calorie tracker", "fake photo", "photo fooled"])
    has_enterprise = any(
        k in titles_text
        for k in ["operacion", "banca", "fintech", "costo", "empresa", "seguridad", "sandbox", "rpa", "compliance", "ceo", "liderazgo", "roi"]
    )
    impact_multiplier = 0.40 if is_toy else (1.20 if has_enterprise else 1.0)
    conf_factor = 0.45 + (0.55 * decision.confianza)

    score_breakdown = {
        "score_final": final_score,
        "confianza_jev": decision.confianza,
        "factor_confianza": round(conf_factor, 3),
        "multiplicador_sinergia": synergy_multiplier,
        "multiplicador_impacto": impact_multiplier,
        "encaje_audiencia": decision.encaje_audiencia,
        "novedad": decision.novedad,
        "fase": decision.fase,
        "gancho": decision.gancho,
        "formato": decision.formato,
    }

    import os
    has_key = bool(os.getenv("TYPESAFE_API_KEY"))
    motor = "TypeSafe Jev System 1 (Live API)" if has_key else "Calibrador Determinista RLCD (Local)"

    return PlaygroundTelemetry(
        tema=tema,
        fuentes=active_fuentes,
        vistas_por_hora=vistas_por_hora,
        preguntas_jev=preguntas_jev,
        decision=decision,
        score_final=final_score,
        crecimiento_label=crecimiento_label,
        score_breakdown=score_breakdown,
        latencia_ms=latencia_ms,
        motor_utilizado=motor,
    )
