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


def test_ingest_image_with_keywords_mode():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        store = VectorStore(db_path=temp_db)
        fake_base64_png = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        source, profile = ingest_knowledge_resource(
            url_o_path="infografia_benchmarks_deepseek_anthropic.png",
            solicitud_usuario="Extraer palabras clave sobre benchmarks de razonamiento y modelos de IA",
            tipo="image",
            modo="keywords",
            titulo="Comparativa Benchmarks DeepSeek R1 vs Claude 3.5 Sonnet",
            image_data=fake_base64_png,
            vector_store=store,
        )

        assert source.tipo == "image"
        assert source.modo_extraccion == "keywords"
        assert source.imagen_preview == fake_base64_png
        assert profile.modo_extraccion == "keywords"
        assert len(profile.palabras_clave) > 0
        assert any(k.lower() in ["benchmarks", "razonamiento", "modelos", "ia", "deepseek r1", "claude 3.5 sonnet"] for k in profile.palabras_clave)
        assert len(profile.entidades_detectadas) > 0
        assert len(profile.enfoques_radar_sugeridos) > 0

        # Verificar que los chunks vectoriales indexaron las keywords
        hits = store.search_similar("benchmarks razonamiento modelos", top_k=3)
        assert len(hits) > 0
        assert hits[0]["source_id"] == source.id
        tags = hits[0].get("tags", [])
        assert "keywords" in tags or "multimodal" in tags

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_ingest_image_with_ganchos_mode():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        store = VectorStore(db_path=temp_db)
        fake_base64_png = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        source, profile = ingest_knowledge_resource(
            url_o_path="thumbnail_viral_open_ai.png",
            solicitud_usuario="Extraer ganchos psicológicos de controversia corporativa",
            tipo="image",
            modo="ganchos",
            titulo="Miniatura de YouTube: Por qué renunciaron los líderes de OpenAI",
            image_data=fake_base64_png,
            vector_store=store,
        )

        assert source.tipo == "image"
        assert source.modo_extraccion == "ganchos"
        assert profile.hook is not None
        assert profile.hook.plantilla_reutilizable != ""
        assert len(profile.plantillas_30x) > 0

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_ingest_image_pool_multi_images():
    """Verifica que un pool de múltiples imágenes se registre con tipo 'image_pool' y persista todo el pool."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        store = VectorStore(db_path=temp_db)
        img1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        img2 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        img3 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg=="

        pool = [img1, img2, img3]
        filenames = ["grafico_mercado_q1.png", "benchmark_rendimiento.jpg", "dashboard_retencion.png"]

        source, profile = ingest_knowledge_resource(
            url_o_path="pool_mercado_q1",
            solicitud_usuario="Analizar métricas de mercado y benchmarks de IA",
            tipo="image_pool",
            modo="completo",
            images_data=pool,
            filenames=filenames,
            vector_store=store,
        )

        assert source.tipo == "image_pool"
        assert source.total_imagenes == 3
        assert len(source.imagenes_pool) == 3
        assert source.imagen_preview == img1
        assert "Pool" in source.titulo or "mercado" in source.titulo.lower()

        # Verificar persistencia en base de datos SQLite
        all_sources = store.get_all_sources()
        assert len(all_sources) == 1
        saved = all_sources[0]
        assert saved.tipo == "image_pool"
        assert saved.total_imagenes == 3
        assert len(saved.imagenes_pool) == 3
        assert saved.imagenes_pool[1] == img2

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_different_images_produce_distinct_keywords():
    """Verifica que imágenes con diferentes nombres, focos y contenidos produzcan palabras clave diferenciadas."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        store = VectorStore(db_path=temp_db)
        img_a = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        img_b = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

        src_a, prof_a = ingest_knowledge_resource(
            url_o_path="kubernetes_docker_microservicios_devops.png",
            solicitud_usuario="Extraer términos de infraestructura contenedores kubernetes devops",
            tipo="image",
            modo="keywords",
            titulo="Arquitectura de Contenedores Kubernetes y Docker",
            image_data=img_a,
            vector_store=store,
        )

        src_b, prof_b = ingest_knowledge_resource(
            url_o_path="finanzas_banca_latam_roi_conciliacion.png",
            solicitud_usuario="Extraer términos de fintech finanzas y banca",
            tipo="image",
            modo="keywords",
            titulo="Conciliación Financiera y Finanzas para Directores",
            image_data=img_b,
            vector_store=store,
        )

        # Las palabras clave de imagen A deben contener términos de infraestructura
        kw_a = [k.lower() for k in prof_a.palabras_clave + prof_a.entidades_detectadas]
        # Las palabras clave de imagen B deben contener términos financieros
        kw_b = [k.lower() for k in prof_b.palabras_clave + prof_b.entidades_detectadas]

        assert any("kubernetes" in k or "docker" in k or "contenedores" in k for k in kw_a)
        assert any("finanzas" in k or "financiera" in k or "banca" in k or "fintech" in k for k in kw_b)

        # No deben ser listas idénticas
        assert set(prof_a.palabras_clave) != set(prof_b.palabras_clave)

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

