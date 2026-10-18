"""Módulo de Base de Conocimiento Vectorial, Procesamiento Multimodal y Perfilado de Estilo para Radar30X."""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from pipeline.knowledge.extractor import (
    build_knowledge_chunks,
    extract_hook_and_profile,
    extract_knowledge_profile,
)
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
    modo: str = "completo",  # "ganchos" | "keywords" | "completo"
    titulo: Optional[str] = None,
    autor: Optional[str] = None,
    image_data: Optional[str] = None,
    images_data: Optional[List[str]] = None,
    filenames: Optional[List[str]] = None,
    vector_store: Optional[VectorStore] = None,
) -> Tuple[KnowledgeSource, KnowledgeProfile]:
    """Flujo completo de ingesta multimodal: transcripción/visión (incluyendo pools de imágenes), extracción de ganchos/keywords y guardado vectorial."""
    store = vector_store or VectorStore()

    pool_list: List[str] = []
    if images_data and isinstance(images_data, list) and len(images_data) > 0:
        pool_list = images_data
    elif image_data:
        pool_list = [image_data]

    # Detección automática de tipo imagen / pool
    if len(pool_list) > 1 or tipo == "image_pool":
        tipo = "image_pool"
    elif (
        tipo == "image"
        or (image_data and image_data.startswith("data:image/"))
        or url_o_path.startswith("data:image/")
        or url_o_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg", ".bmp"))
        or len(pool_list) == 1
    ):
        tipo = "image"

    # 1. Generar ID determinista basado en URL o contenido
    id_seed = url_o_path if not url_o_path.startswith("data:image/") else url_o_path[:100] + str(len(url_o_path))
    if pool_list:
        id_seed += f"-pool-{len(pool_list)}-{sum(len(x) for x in pool_list)}"
    source_id = f"knw-{hashlib.md5(id_seed.encode('utf-8')).hexdigest()[:12]}"

    # 2. Transcripción / procesamiento multimodal
    full_text, segments, duration = transcribe_resource(
        url_o_path=url_o_path,
        tipo=tipo,
        image_data=pool_list[0] if pool_list else image_data,
        images_data=pool_list if len(pool_list) > 1 else None,
        filenames=filenames,
        solicitud_usuario=solicitud_usuario,
    )

    # 3. Título por defecto
    if not titulo:
        if tipo == "image_pool":
            final_title = f"Pool de {len(pool_list)} imágenes analizadas"
        elif tipo == "image":
            final_title = f"Imagen analizada ({url_o_path.split('/')[-1][:25]})" if not url_o_path.startswith("data:") else "Captura / Gráfico multimodal"
        else:
            final_title = f"Recurso multimedia ({url_o_path.split('/')[-1][:30]})"
    else:
        final_title = titulo

    final_author = autor or ("Referente Visual" if tipo in ("image", "image_pool") else "Referente / Creador")

    # 4. Preview de imagen si aplica
    imagen_preview = None
    if tipo in ("image", "image_pool"):
        if pool_list and pool_list[0].startswith("data:image/"):
            imagen_preview = pool_list[0]
        elif image_data and image_data.startswith("data:image/"):
            imagen_preview = image_data
        elif url_o_path.startswith(("http://", "https://", "data:image/")):
            imagen_preview = url_o_path

    # 5. Extraer perfil según el modo solicitado (ganchos, keywords o completo)
    primary_image = pool_list[0] if pool_list else (image_data or (url_o_path if url_o_path.startswith("data:image/") else None))
    profile = extract_knowledge_profile(
        source_id=source_id,
        titulo=final_title,
        transcript_text=full_text,
        segments=segments,
        solicitud_usuario=solicitud_usuario,
        modo=modo,
        image_data=primary_image,
        tipo=tipo,
    )

    # 6. Crear Chunks vectoriales (incluye chunks de transcripción, keywords y ganchos)
    chunks = build_knowledge_chunks(source_id, segments, store, profile=profile)

    # 7. Modelo de fuente
    source = KnowledgeSource(
        id=source_id,
        tipo=tipo,  # type: ignore
        modo_extraccion=modo,  # type: ignore
        url_o_path=url_o_path if not url_o_path.startswith("data:image/") else f"pool-upload-{source_id[:8]}" if tipo == "image_pool" else f"image-upload-{source_id[:8]}",
        imagen_preview=imagen_preview,
        imagenes_pool=pool_list,
        total_imagenes=max(1, len(pool_list)),
        titulo=final_title,
        autor=final_author,
        duracion_segundos=round(duration, 2),
        solicitud_usuario=solicitud_usuario,
        transcripcion_resumen=full_text[:350] + ("..." if len(full_text) > 350 else ""),
        perfil=profile,
    )

    # 8. Persistir en SQLite (radar.db)
    store.save_source_and_profile(source, profile, chunks)
    return source, profile


def search_knowledge_base(
    query: str,
    top_k: int = 5,
    tag_filter: Optional[str] = None,
    vector_store: Optional[VectorStore] = None,
) -> List[Dict[str, Any]]:
    """Consulta la base vectorial semántica para recuperar ganchos, palabras clave y conceptos."""
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
    "extract_knowledge_profile",
    "extract_hook_and_profile",
]
