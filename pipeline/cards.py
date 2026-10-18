"""Módulo de materialización de Tarjetas de Narrativa (Narrative Cards) para RAG.

Sintetiza la evolución temporal, veredictos empíricos y ganchos de cada narrativa en un bloque
semántico denso y estructurado, optimizado para indexación vectorial y recuperación precisa
sin ruido de publicaciones individuales crudas.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from pipeline.db import Database
from pipeline.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


def format_narrative_card(
    narrative_id: str,
    tema: str,
    fase: str,
    first_seen: Optional[str] = None,
    pico_fecha: Optional[str] = None,
    semanas_desde_pico: int = 0,
    fuentes: Optional[List[str]] = None,
    gancho: str = "opinion",
    formato: str = "video_corto",
    veredicto: str = "valido",
    veracidad_p: float = 0.8,
    humo_p: float = 0.1,
    novedad: float = 1.0,
    ratio_copias: float = 0.0,
    sparkline: str = ".:oO*",
    por_que: str = "",
    adaptacion_30x: str = "",
    evidencias: Optional[List[str]] = None,
) -> str:
    """Construye el texto condensado y estructurado de la tarjeta de narrativa para RAG."""
    fuentes_str = ", ".join(fuentes) if fuentes else "Web abierta"
    pico_str = pico_fecha if pico_fecha else "ninguno detectado"
    if semanas_desde_pico > 0:
        pico_str += f" (hace {semanas_desde_pico} semanas)"

    evidencia_str = " | ".join(evidencias[:3]) if evidencias else "Evidencia verificada"
    por_que_str = f" | por_que: {por_que}" if por_que else ""
    adaptacion_str = f" | adaptacion_30x: {adaptacion_30x}" if adaptacion_30x else ""

    card_text = (
        f"{tema} | fase: {fase} | first_seen: {first_seen or 'reciente'} | pico: {pico_str} | "
        f"fuentes: {fuentes_str} | gancho dominante: {gancho} | formato: {formato} | "
        f"veredicto: {veredicto} (veracidad: {int(veracidad_p*100)}%, humo: {int(humo_p*100)}%) | "
        f"novedad: {int(novedad*100)}% | ratio_copias: {int(ratio_copias*100)}% | "
        f"sparkline: [{sparkline}]{por_que_str}{adaptacion_str} | evidencia: {evidencia_str}"
    )
    return card_text


def materialize_all_narrative_cards(
    db: Optional[Database] = None,
    vector_store: Optional[VectorStore] = None,
    report_data: Optional[Dict[str, Any]] = None,
) -> int:
    """Genera y guarda en SQLite las tarjetas de narrativa con sus embeddings correspondientes.

    Recupera el último reporte generado y las narrativas activas, construye la tarjeta
    sintética de cada una e invalida la caché de respuestas para mantener sincronizado el chatbot.
    """
    db = db or Database()
    vector_store = vector_store or VectorStore()

    if not report_data:
        report_data = db.get_latest_report()

    count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Si tenemos reporte disponible, materializar los temas del reporte
    if report_data and "top_temas" in report_data:
        for idx, t in enumerate(report_data.get("top_temas", [])):
            tema_nombre = t.get("tema") or f"Tema #{idx+1}"
            narrative_id = t.get("narrative_id") or f"top_{idx+1}_{abs(hash(tema_nombre)) % 1000000:06x}"

            # Extraer veredicto del crítico si existe
            vc = t.get("veredicto_critico") or {}
            veredicto = vc.get("veredicto") or "valido"
            veracidad_p = float(vc.get("veracidad_p", 0.8))
            humo_p = float(vc.get("humo_p", 0.1))

            card_text = format_narrative_card(
                narrative_id=narrative_id,
                tema=tema_nombre,
                fase=t.get("fase", "emergente"),
                first_seen=report_data.get("semana"),
                pico_fecha=None,
                semanas_desde_pico=0,
                fuentes=t.get("fuentes", []),
                gancho=t.get("gancho", "opinion"),
                formato=t.get("formato", "video_corto"),
                veredicto=veredicto,
                veracidad_p=veracidad_p,
                humo_p=humo_p,
                novedad=float(t.get("novedad", 1.0)),
                ratio_copias=0.0,
                sparkline=t.get("sparkline", ".:oO*"),
                por_que=t.get("por_que", ""),
                adaptacion_30x=t.get("adaptacion_30x", ""),
                evidencias=t.get("evidencia", []),
            )

            # Generar embedding vectorial
            vec = vector_store.generate_embedding(card_text)
            vector_blob = VectorStore.pack_embedding(vec)

            # Guardar en base de datos
            db.save_narrative_card(narrative_id=narrative_id, texto=card_text, embedding=vector_blob)
            count += 1

    # 2. Materializar también narrativas de la tabla `narratives` si no estaban en el reporte
    narratives = db.get_narratives(limit=50)
    for n in narratives:
        n_id = n["id"]
        # Verificar si ya fue guardada
        if db.get_narrative_card(n_id):
            continue

        verdict = db.get_verdict(n_id) or {}
        card_text = format_narrative_card(
            narrative_id=n_id,
            tema=n["nombre"],
            fase=n.get("fase", "emergente"),
            first_seen=n.get("first_seen"),
            pico_fecha=n.get("pico_fecha"),
            semanas_desde_pico=n.get("semanas_desde_pico", 0),
            fuentes=["Ecosistema Tech"],
            gancho="analisis",
            formato="video_corto",
            veredicto=verdict.get("veredicto", "valido"),
            veracidad_p=verdict.get("veracidad_p", 0.75),
            humo_p=verdict.get("humo_p", 0.15),
            novedad=n.get("novelty", 0.8),
            ratio_copias=n.get("ratio_copias", 0.0),
            sparkline=n.get("sparkline", ".:oO*"),
            por_que="",
            adaptacion_30x="",
            evidencias=[],
        )

        vec = vector_store.generate_embedding(card_text)
        vector_blob = VectorStore.pack_embedding(vec)
        db.save_narrative_card(narrative_id=n_id, texto=card_text, embedding=vector_blob)
        count += 1

    # 3. Invalidar la caché de respuestas
    db.invalidate_answers_cache()
    logger.info("Materializadas %d tarjetas de narrativa en SQLite.", count)
    return count
