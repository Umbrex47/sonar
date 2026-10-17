"""Módulo de Base de Conocimiento Vectorial y Perfilado de Estilo para Radar30X."""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from pipeline.knowledge.extractor import build_knowledge_chunks, extract_hook_and_profile
from pipeline.knowledge.models import (
    HookAnalysis,
    KnowledgeChunk,
    KnowledgeProfile,
    KnowledgeSource,
)
from pipeline.knowledge.transcriber import transcribe_resource
from pipeline.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


def ingest_knowledge_resource(
    url_o_path: str,
    solicitud_usuario: str,
    tipo: str = "youtube",
    titulo: Optional[str] = None,
    autor: Optional[str] = None,
    vector_store: Optional[VectorStore] = None,
) -> Tuple[KnowledgeSource, KnowledgeProfile]:
    """Flujo completo de ingesta: transcripción, extracción de estilo guiado por solicitud, y guardado vectorial."""
    store = vector_store or VectorStore()

    # 1. Generar ID determinista basado en URL
    source_id = f"knw-{hashlib.md5(url_o_path.encode('utf-8')).hexdigest()[:12]}"

    # 2. Transcripción
    full_text, segments, duration = transcribe_resource(url_o_path, tipo=tipo)

    # 3. Título por defecto si no viene provisto
    final_title = titulo or f"Recurso de video ({url_o_path.split('/')[-1][:30]})"
    final_author = autor or "Referente / Creador"

    # 4. Extraer ganchos y perfil narrativo guiado por solicitud
    profile = extract_hook_and_profile(
        source_id=source_id,
        titulo=final_title,
        transcript_text=full_text,
        segments=segments,
        solicitud_usuario=solicitud_usuario,
    )

    # 5. Crear Chunks vectoriales
    chunks = build_knowledge_chunks(source_id, segments, store)

    # 6. Fuente
    source = KnowledgeSource(
        id=source_id,
        tipo=tipo,  # type: ignore
        url_o_path=url_o_path,
        titulo=final_title,
        autor=final_author,
        duracion_segundos=round(duration, 2),
        solicitud_usuario=solicitud_usuario,
        transcripcion_resumen=full_text[:350] + ("..." if len(full_text) > 350 else ""),
        perfil=profile,
    )

    # 7. Persistir en SQLite (radar.db)
    store.save_source_and_profile(source, profile, chunks)
    return source, profile


def search_knowledge_base(
    query: str,
    top_k: int = 5,
    tag_filter: Optional[str] = None,
    vector_store: Optional[VectorStore] = None,
) -> List[Dict[str, Any]]:
    """Consulta la base vectorial semántica para recuperar ganchos y conceptos relevantes."""
    store = vector_store or VectorStore()
    return store.search_similar(query, top_k=top_k, tag_filter=tag_filter)


def list_knowledge_sources(vector_store: Optional[VectorStore] = None) -> List[KnowledgeSource]:
    """Lista todos los recursos y perfiles de estilo registrados."""
    store = vector_store or VectorStore()
    return store.get_all_sources()


__all__ = [
    "VectorStore",
    "KnowledgeSource",
    "KnowledgeProfile",
    "HookAnalysis",
    "KnowledgeChunk",
    "ingest_knowledge_resource",
    "search_knowledge_base",
    "list_knowledge_sources",
]
