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

    # 1. Tomar decisión con Jev (con trazabilidad completa)
    decision = decide_cluster(cluster)
    latencia_ms = round((time.perf_counter() - t0) * 1000, 1)

    # 2. Calcular desglose de scoring
    final_score, crecimiento_label = calculate_topic_score(cluster, decision)

    # 3. Mapear las 5 preguntas con las respuestas vivas de JEV
    propositos = {
        "q1_fase": "Determinar si es una oportunidad emergente temprana o si el mercado ya está saturado de copias.",
        "q2_gancho": "Identificar el mecanismo cognitivo para capturar la atención en los primeros 10 segundos.",
        "q3_formato": "Recomendar si debe ser un Short/Reel, un Carrusel en LinkedIn o una Masterclass técnica.",
        "q4_novedad": "Filtrar refritos o herramientas del año anterior que reviven artificialmente.",
        "q5_encaje_latam": "Evaluar si aborda costos, ROI, operaciones, seguridad o personas en empresas de la región.",
    }

    preguntas_jev = []
    if decision.audit and decision.audit.preguntas:
        for q in decision.audit.preguntas:
            preguntas_jev.append({
                "id": q.id,
                "pregunta": q.pregunta,
                "respuesta": q.respuesta,
                "score": q.score,
                "razonamiento": q.razonamiento,
                "proposito": propositos.get(q.id, "Validar impacto y aplicabilidad para directivos en LatAm."),
            })
    else:
        # Fallback estructurado
        preguntas_jev = [
            {"id": "q1_fase", "pregunta": "¿En qué fase de adopción se encuentra?", "respuesta": decision.fase, "score": decision.novedad, "razonamiento": f"Clasificado en fase '{decision.fase}'.", "proposito": propositos["q1_fase"]},
            {"id": "q2_gancho", "pregunta": "¿Cuál es el gancho psicológico?", "respuesta": decision.gancho, "score": 0.85, "razonamiento": f"Gancho óptimo: {decision.gancho}.", "proposito": propositos["q2_gancho"]},
            {"id": "q3_formato", "pregunta": "¿Cuál es el formato nativo ideal?", "respuesta": decision.formato, "score": 0.80, "razonamiento": f"Formato: {decision.formato}.", "proposito": propositos["q3_formato"]},
            {"id": "q4_novedad", "pregunta": "¿Qué probabilidad de novedad emergente existe?", "respuesta": f"{int(decision.novedad * 100)}%", "score": decision.novedad, "razonamiento": "Filtro temporal activo.", "proposito": propositos["q4_novedad"]},
            {"id": "q5_encaje_latam", "pregunta": "¿Qué nivel de relevancia ejecutiva tiene?", "respuesta": f"{int(decision.encaje_audiencia * 100)}%", "score": decision.encaje_audiencia, "razonamiento": "Afinidad con toma de decisiones.", "proposito": propositos["q5_encaje_latam"]},
        ]

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

    veredicto = decision.audit.veredicto if decision.audit else ("DESCARTADO" if final_score < 0.35 else "APROBADO")
    motivo_veredicto = decision.audit.motivo_veredicto if decision.audit else ""
    palabras_clave = decision.audit.palabras_clave_detectadas if decision.audit else []

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
        "veredicto": veredicto,
        "motivo_veredicto": motivo_veredicto,
        "palabras_clave": palabras_clave,
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
