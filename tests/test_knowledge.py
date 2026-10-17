"""Pruebas unitarias para la Base de Conocimiento Vectorial y Extracción de Ganchos."""

import os
import tempfile
import pytest

from pipeline.knowledge.models import HookAnalysis, KnowledgeProfile, KnowledgeSource, KnowledgeChunk
from pipeline.knowledge.vector_store import VectorStore
from pipeline.knowledge.transcriber import extract_youtube_video_id, transcribe_resource
from pipeline.knowledge.extractor import extract_hook_and_profile, build_knowledge_chunks
from pipeline.knowledge import ingest_knowledge_resource, search_knowledge_base


def test_extract_youtube_video_id():
    url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url2 = "https://youtu.be/dQw4w9WgXcQ?si=abc"
    url3 = "https://youtube.com/shorts/dQw4w9WgXcQ"
    assert extract_youtube_video_id(url1) == "dQw4w9WgXcQ"
    assert extract_youtube_video_id(url2) == "dQw4w9WgXcQ"
    assert extract_youtube_video_id(url3) == "dQw4w9WgXcQ"


def test_vector_store_save_and_search():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        store = VectorStore(db_path=temp_db)

        # 1. Crear modelos
        source = KnowledgeSource(
            id="test-source-1",
            tipo="youtube",
            url_o_path="https://youtube.com/watch?v=test1234567",
            titulo="Cómo escalar agentes de IA en banca",
            autor="Carlos Mendoza",
            solicitud_usuario="Extraer ganchos contraintuitivos para ejecutivos",
            transcripcion_resumen="El 90% de los bancos fracasan al implementar agentes por no usar sandboxes...",
        )

        hook = HookAnalysis(
            tipo_gancho="dato_contraintuitivo",
            texto_primeros_15s="El 90% de los bancos fracasan al implementar agentes...",
            analisis_gancho="Ruptura de creencia convencional sobre chatbots",
            plantilla_reutilizable="El [X]% de las empresas fallan en [Y] porque ignoran [Z]",
        )

        profile = KnowledgeProfile(
            source_id="test-source-1",
            hook=hook,
            estructura_narrativa=[{"etapa": "Hook", "segundos": "0-15s", "proposito": "Atención"}],
            tono_y_voz="Autoridad ejecutiva",
            conceptos_clave=["Sandboxing", "Banca", "Agentes"],
            plantillas_30x=["Video corto: El error bancario de la IA"],
            resumen_ejecutivo="Lección de arquitectura segura",
        )

        emb1 = store.generate_embedding("agentes de inteligencia artificial en el sector financiero y bancario")
        chunk1 = KnowledgeChunk(
            id="chk-1",
            source_id="test-source-1",
            chunk_index=0,
            timestamp_inicio=0.0,
            timestamp_fin=30.0,
            texto="Los bancos en Colombia y México están integrando agentes para conciliación contable.",
            embedding=emb1,
            tags=["banca", "fintech"],
        )

        store.save_source_and_profile(source, profile, [chunk1])

        # 2. Recuperar fuentes
        sources = store.get_all_sources()
        assert len(sources) == 1
        assert sources[0].id == "test-source-1"
        assert sources[0].perfil is not None
        assert sources[0].perfil.hook.tipo_gancho == "dato_contraintuitivo"

        # 3. Búsqueda semántica
        results = store.search_similar("banca finanzas agentes", top_k=2)
        assert len(results) > 0
        assert results[0]["source_id"] == "test-source-1"
        assert results[0]["score"] > 0.0

        # 4. Eliminar fuente
        deleted = store.delete_source("test-source-1")
        assert deleted is True
        assert len(store.get_all_sources()) == 0

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_ingest_knowledge_resource_end_to_end():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        store = VectorStore(db_path=temp_db)
        source, profile = ingest_knowledge_resource(
            url_o_path="https://www.youtube.com/watch?v=mocktest123",
            solicitud_usuario="Extraer ganchos para video de 60 segundos sobre productividad",
            tipo="youtube",
            titulo="Productividad Extrema con Agentes Autónomos",
            autor="Tech LatAm",
            vector_store=store,
        )

        assert source.id.startswith("knw-")
        assert source.titulo == "Productividad Extrema con Agentes Autónomos"
        assert profile.hook.tipo_gancho in [
            "dato_contraintuitivo",
            "pregunta_quiebre",
            "afirmacion_audaz",
            "historia_personal",
            "contraste",
        ]
        assert len(profile.plantillas_30x) > 0

        # Verificar que se pueda buscar
        search_hits = search_knowledge_base("agentes de productividad", vector_store=store)
        assert len(search_hits) > 0
        assert search_hits[0]["source_id"] == source.id

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)
