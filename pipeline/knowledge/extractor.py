"""Extractor de ganchos, estructura narrativa y perfil de estilo guiado por solicitud del usuario."""

import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from pipeline.knowledge.models import (
    HookAnalysis,
    KnowledgeChunk,
    KnowledgeProfile,
    KnowledgeSource,
)
from pipeline.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


def extract_hook_and_profile(
    source_id: str,
    titulo: str,
    transcript_text: str,
    segments: List[Dict[str, Any]],
    solicitud_usuario: str,
) -> KnowledgeProfile:
    """Extrae el estilo de gancho, estructura narrativa y fórmulas adaptadas a la solicitud del usuario."""
    # 1. Extraer los primeros 15-20 segundos del transcript para análisis de gancho
    first_15s_segments = [s for s in segments if s.get("start", 0.0) <= 20.0]
    first_15s_text = " ".join([s["text"] for s in first_15s_segments]) if first_15s_segments else transcript_text[:200]

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-placeholder"):
        try:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            prompt = f"""Eres el analista senior de narrativa y ganchos de 30X, medio líder de IA para directivos en Latinoamérica.
Analiza la siguiente transcripción de video y responde estrictamente con un JSON según las instrucciones y la solicitud del usuario.

SOLICITUD ESPECÍFICA DEL USUARIO:
"{solicitud_usuario}"

TÍTULO DEL CONTENIDO:
"{titulo}"

PRIMEROS 15 SEGUNDOS (GANCHO):
"{first_15s_text}"

TRANSCRIPCIÓN COMPLETA:
\"\"\"{transcript_text[:5000]}\"\"\"

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
  "tipo_gancho": "dato_contraintuitivo | pregunta_quiebre | afirmacion_audaz | historia_personal | contraste",
  "texto_primeros_15s": "{first_15s_text[:200]}",
  "analisis_gancho": "Explicación de por qué este gancho funciona y cómo captura la atención según la solicitud",
  "plantilla_reutilizable": "Fórmula reutilizable lista para usar en nuevos guiones de 30X",
  "estructura_narrativa": [
    {{"etapa": "Hook", "segundos": "0-15s", "proposito": "Captar atención inmediata"}},
    {{"etapa": "Tensión", "segundos": "15-45s", "proposito": "Presentar el problema real en las empresas"}},
    {{"etapa": "Payoff", "segundos": "45-90s", "proposito": "Demostración o dato de solución"}},
    {{"etapa": "CTA", "segundos": "Final", "proposito": "Llamada a la acción"}}
  ],
  "tono_y_voz": "autoridad ejecutiva | provocador y directo | analítico de producto",
  "conceptos_clave": ["concepto1", "concepto2", "concepto3"],
  "plantillas_30x": [
    "Fórmula 1 de adaptación para 30X",
    "Fórmula 2 de adaptación para 30X"
  ],
  "resumen_ejecutivo": "Síntesis en 2 oraciones de lo que enseña este contenido"
}}
"""
            with httpx.Client(timeout=20.0, trust_env=False) as client:
                res = client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                    },
                )
                if res.status_code == 200:
                    data = res.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(data)
                    hook = HookAnalysis(
                        tipo_gancho=parsed.get("tipo_gancho", "dato_contraintuitivo"),
                        texto_primeros_15s=parsed.get("texto_primeros_15s", first_15s_text[:200]),
                        analisis_gancho=parsed.get("analisis_gancho", "Gancho de alta retención basado en contraste"),
                        plantilla_reutilizable=parsed.get("plantilla_reutilizable", "El [X]% de las empresas cometen el error de [Y]..."),
                    )
                    return KnowledgeProfile(
                        source_id=source_id,
                        hook=hook,
                        estructura_narrativa=parsed.get("estructura_narrativa", []),
                        tono_y_voz=parsed.get("tono_y_voz", "Autoridad ejecutiva y analítica"),
                        conceptos_clave=parsed.get("conceptos_clave", ["Agentes", "ROI", "Operaciones"]),
                        plantillas_30x=parsed.get("plantillas_30x", []),
                        resumen_ejecutivo=parsed.get("resumen_ejecutivo", ""),
                    )
        except Exception as e:
            logger.warning("Fallo al consultar LLM para perfil de gancho: %s. Usando extractor determinista.", e)

    # Extractor determinista y analítico calibrado (Zero-cost fallback)
    txt_lower = transcript_text.lower()
    first_lower = first_15s_text.lower()

    if any(k in first_lower for k in ["por qué", "cómo", "qué pasa si", "sabías"]):
        tipo_gancho = "pregunta_quiebre"
        analisis = f"Gancho socrático que abre un bucle de curiosidad alineado a la solicitud: '{solicitud_usuario}'."
        plantilla = "¿Por qué las mejores empresas de LatAm están abandonando [Herramienta tradicional] por [Nueva IA]?"
    elif any(k in first_lower for k in ["error", "cuidado", "peligro", "no uses", "falso"]):
        tipo_gancho = "afirmacion_audaz"
        analisis = f"Gancho de aversión a la pérdida y alerta operativa enfocado en: '{solicitud_usuario}'."
        plantilla = "El error número 1 al implementar [Tendencia IA] que le cuesta miles de dólares a tu empresa."
    else:
        tipo_gancho = "dato_contraintuitivo"
        analisis = f"Gancho que rompe la expectativa común y presenta una métrica contundente según: '{solicitud_usuario}'."
        plantilla = "El 90% de los líderes creen que [Mito], pero la realidad en producción es [Dato duro]."

    hook = HookAnalysis(
        tipo_gancho=tipo_gancho,
        texto_primeros_15s=first_15s_text[:250],
        analisis_gancho=analisis,
        plantilla_reutilizable=plantilla,
    )

    estructura = [
        {"etapa": "Hook", "segundos": "0-15s", "proposito": "Captar atención con dato de ruptura"},
        {"etapa": "Tensión", "segundos": "15-45s", "proposito": "Demostrar el costo oculto de ignorar esta tendencia"},
        {"etapa": "Payoff / Caso", "segundos": "45-90s", "proposito": "Explicar la arquitectura o flujo práctico"},
        {"etapa": "CTA", "segundos": "Final", "proposito": "Invitar al debate estratégico en comentarios"},
    ]

    return KnowledgeProfile(
        source_id=source_id,
        hook=hook,
        estructura_narrativa=estructura,
        tono_y_voz="Autoridad ejecutiva, directo y periodístico",
        conceptos_clave=["Automatización", "Retención", "Liderazgo en IA", "ROI"],
        plantillas_30x=[
            f"Short / Reel: '{plantilla}' + desglose en pantalla",
            f"Carrusel LinkedIn: '3 lecciones de {titulo} aplicadas a directivos en LatAm'",
        ],
        resumen_ejecutivo=f"Recurso analizado bajo solicitud '{solicitud_usuario}'. Enseña a estructurar ganchos de retención inmediata y simplificar conceptos técnicos para líderes corporativos.",
    )


def build_knowledge_chunks(
    source_id: str,
    segments: List[Dict[str, Any]],
    vector_store: VectorStore,
    chunk_size_words: int = 80,
) -> List[KnowledgeChunk]:
    """Divide la transcripción en chunks semánticos contiguos con marcas de tiempo y genera sus embeddings."""
    chunks: List[KnowledgeChunk] = []
    current_words: List[str] = []
    chunk_start = 0.0
    chunk_end = 0.0
    chunk_idx = 0

    for seg in segments:
        words = seg.get("text", "").split()
        if not words:
            continue

        if not current_words:
            chunk_start = float(seg.get("start", 0.0))

        current_words.extend(words)
        chunk_end = float(seg.get("start", 0.0)) + float(seg.get("duration", 0.0))

        if len(current_words) >= chunk_size_words:
            chunk_text = " ".join(current_words)
            chunk_id = f"{source_id}-chk-{chunk_idx}"
            emb = vector_store.generate_embedding(chunk_text)

            chunks.append(
                KnowledgeChunk(
                    id=chunk_id,
                    source_id=source_id,
                    chunk_index=chunk_idx,
                    timestamp_inicio=round(chunk_start, 2),
                    timestamp_fin=round(chunk_end, 2),
                    texto=chunk_text,
                    embedding=emb,
                    tags=["transcripcion", "video_knowledge"],
                )
            )
            chunk_idx += 1
            # Mantener un solapamiento (overlap) del 20%
            current_words = current_words[-15:]
            chunk_start = chunk_end - 5.0

    # Último remanente si queda texto
    if current_words:
        chunk_text = " ".join(current_words)
        chunk_id = f"{source_id}-chk-{chunk_idx}"
        emb = vector_store.generate_embedding(chunk_text)
        chunks.append(
            KnowledgeChunk(
                id=chunk_id,
                source_id=source_id,
                chunk_index=chunk_idx,
                timestamp_inicio=round(chunk_start, 2),
                timestamp_fin=round(chunk_end, 2),
                texto=chunk_text,
                embedding=emb,
                tags=["transcripcion", "video_knowledge"],
            )
        )

    return chunks
