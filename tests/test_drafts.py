"""Pruebas unitarias para el gestor de borradores (drafts/manager.py)."""

from pathlib import Path
import pytest

from drafts.manager import (
    DraftManager,
    parse_frontmatter,
    serialize_frontmatter,
    slugify,
)
from pipeline.db import Database


def test_slugify():
    assert slugify("Guía de Seguridad para Agentes") == "guía-de-seguridad-para-agentes"
    assert slugify("¿Qué es Model Context Protocol? (MCP)") == "qué-es-model-context-protocol-mcp"
    assert slugify("   ") == "borrador"


def test_frontmatter_parsing_and_serialization():
    fm = {
        "draft_id": 42,
        "narrative_id": "c1234",
        "estado": "borrador",
        "formato": "video_corto",
        "gancho": "opinion",
        "evidencia": ["https://hn.com/item/1", "https://github.com/test"],
    }
    body = "# Título del Borrador\n\nCuerpo del guion con detalles."

    serialized = serialize_frontmatter(fm, body)
    assert "draft_id: 42" in serialized
    assert "https://github.com/test" in serialized

    parsed_fm, parsed_body = parse_frontmatter(serialized)
    assert parsed_fm["draft_id"] == 42
    assert parsed_fm["estado"] == "borrador"
    assert len(parsed_fm["evidencia"]) == 2
    assert "Cuerpo del guion con detalles." in parsed_body


def test_draft_lifecycle_and_state_machine(tmp_path):
    db_file = str(tmp_path / "test_drafts.db")
    drafts_dir = str(tmp_path / "drafts")
    db = Database(db_path=db_file)
    dm = DraftManager(db=db, base_dir=drafts_dir)

    # 1. Crear nuevo borrador
    created = dm.create_draft(
        narrative_id="test_nar_10",
        titulo="Agentes con Memoria de 90 Días",
        formato="video_corto",
        gancho="contraintuitivo",
        evidencia=["https://github.com/test/agents"],
    )
    draft_id = created["id"]
    assert draft_id is not None
    assert created["estado"] == "borrador"
    assert Path(created["path"]).exists()

    # 2. Transición válida: borrador -> en_revision
    res1 = dm.update_status(draft_id, "en_revision")
    assert res1["nuevo_estado"] == "en_revision"

    # 3. Transición inválida: en_revision -> publicado (debe fallar)
    with pytest.raises(ValueError) as excinfo:
        dm.update_status(draft_id, "publicado")
    assert "Transición inválida" in str(excinfo.value)

    # 4. Transiciones válidas hasta publicado: en_revision -> aprobado -> publicado
    res2 = dm.update_status(draft_id, "aprobado")
    assert res2["nuevo_estado"] == "aprobado"

    res3 = dm.update_status(draft_id, "publicado")
    assert res3["nuevo_estado"] == "publicado"

    # 5. Verificar versiones registradas en base de datos
    versions = db.get_draft_versions(draft_id)
    assert len(versions) >= 4  # v1 creación, v2 en_revision, v3 aprobado, v4 publicado

    # 6. Listado filtrado por estado
    pub_list = dm.list_drafts(estado="publicado")
    assert len(pub_list) == 1
    assert pub_list[0]["id"] == draft_id


def test_draft_diff_generation(tmp_path):
    db_file = str(tmp_path / "test_diff.db")
    drafts_dir = str(tmp_path / "drafts")
    db = Database(db_path=db_file)
    dm = DraftManager(db=db, base_dir=drafts_dir)

    created = dm.create_draft(
        titulo="Prueba de Diff",
        formato="hilo",
        gancho="tutorial",
    )
    draft_id = created["id"]

    # Al crearse, no hay diff de versiones anteriores
    diff0 = dm.get_diff(draft_id)
    assert "No hay suficientes versiones" in diff0 or "diff" in diff0

    # Actualizar estado a en_revision
    dm.update_status(draft_id, "en_revision")
    diff1 = dm.get_diff(draft_id)
    assert "-estado: borrador" in diff1 or "+estado: en_revision" in diff1 or "diff" in diff1


def test_generate_draft_structure_and_no_placeholders():
    from drafts.generator import generate_draft_body_llm

    body = generate_draft_body_llm(
        titulo="Lanzamiento de DeepSeek v3 con Destilación Abierta",
        formato="video_corto",
        gancho="contraste",
        evidencia=["https://github.com/deepseek-ai/DeepSeek-V3", "https://huggingface.co/deepseek"],
        narrative_context={
            "por_que": "Destilación de alta eficiencia que reduce factura en 80%.",
            "por_que_audiencia": "Permite a empresas LatAm desplegar modelos sin depender de proveedores de EE.UU.",
            "adaptacion_30x": "Comparativa de costos por millón de tokens en video de 60s.",
            "fase": "Crecimiento",
        },
    )

    # Verificar que contiene las secciones editoriales clave
    assert "# Lanzamiento de DeepSeek v3 con Destilación Abierta" in body
    assert "## 🎯 Ganchos de Apertura" in body
    assert "## 📝 Guion y Estructura Editorial" in body
    assert "## 💼 Ángulo Ejecutivo 30X" in body
    assert "## 🔍 Evidencia y Fuentes de Respaldo" in body
    assert "## 📋 Notas de Producción" in body

    # Verificar que no contiene corchetes de placeholder vacíos del código viejo
    assert "[Gancho de apertura contundente]" not in body
    assert "[Cuestionamiento directo a la audiencia directiva]" not in body
    assert "[Hecho concreto vs expectativa común]" not in body


def test_create_draft_with_narrative_context(tmp_path):
    db_file = str(tmp_path / "test_nar_draft.db")
    drafts_dir = str(tmp_path / "drafts")
    db = Database(db_path=db_file)

    # Simular un reporte en DB
    db.save_report(
        report_id="rep_test_01",
        semana="2026-W42",
        payload={
            "semana": "2026-W42",
            "top_temas": [
                {
                    "posicion": 1,
                    "narrative_id": "nar_01",
                    "tema": "Sandboxing y Aislamiento para Agentes Autónomos",
                    "formato": "video_corto",
                    "gancho": "seguridad",
                    "por_que": "Casos de inyecciones de código en entornos no supervisados.",
                    "por_que_audiencia": "Evita vulnerabilidades operativas en fintech y banca.",
                    "adaptacion_30x": "Guía práctica de mitigación en 3 capas.",
                    "evidencia": ["https://github.com/safebox/agent-sandbox"],
                }
            ],
        },
    )

    dm = DraftManager(db=db, base_dir=drafts_dir)
    draft = dm.create_draft(narrative_id="nar_01")

    assert draft["id"] is not None
    assert draft["titulo"] == "Sandboxing y Aislamiento para Agentes Autónomos"
    assert draft["formato"] == "video_corto"

    content = dm.get_draft(draft["id"])
    body = content["body"]
    assert "Ganchos de Apertura" in body
    assert "https://github.com/safebox/agent-sandbox" in body
    assert "[Gancho de apertura contundente]" not in body

