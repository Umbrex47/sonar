"""Tests unitarios para la conexión del Chatbot con modelos ligeros y RAG abierto (Nivel T1)."""

import pytest
from chat.open_model import (
    retrieve_relevant_cards,
    answer_open_question,
    _deterministic_open_fallback,
)
from chat.router import route_query
from chat.service import ChatService
from pipeline.db import Database


@pytest.fixture
def db_with_cards(tmp_path):
    """Base de datos temporal con tarjetas de narrativa para pruebas."""
    db_file = str(tmp_path / "test_open_chat.db")
    db = Database(db_path=db_file)
    db.init_db()

    # Insertar un par de tarjetas de prueba
    db.save_narrative_card(
        narrative_id="top_1",
        texto=(
            "Sandboxing y Seguridad de Agentes de IA | fase: emergente | "
            "fuentes: GitHub, HackerNews | gancho dominante: tutorial | "
            "veredicto: valido (veracidad: 90%, humo: 5%) | "
            "evidencia: https://github.com/aws-safebox/aws-safebox"
        ),
    )
    db.save_narrative_card(
        narrative_id="top_2",
        texto=(
            "Modelos de Razonamiento y Reducción de Costos con DeepSeek | fase: crecimiento | "
            "fuentes: YouTube, GoogleNews | gancho dominante: contraste | "
            "veredicto: valido (veracidad: 85%, humo: 10%) | "
            "evidencia: https://youtube.com/watch?v=deepseek-demo"
        ),
    )
    return db


def test_router_routes_open_questions():
    """El router debe enviar preguntas exploratorias y estratégicas a T1 (pregunta_abierta)."""
    # Pregunta abierta con "cómo"
    d1 = route_query("¿Cómo puedo implementar sandboxing en mis agentes?")
    assert d1.intencion == "pregunta_abierta"
    assert d1.nivel == "T1"

    # Pregunta abierta con "explícame"
    d2 = route_query("Explícame el impacto de DeepSeek en los costos de inferencia")
    assert d2.intencion == "pregunta_abierta"
    assert d2.nivel == "T1"

    # Pregunta abierta con "compara"
    d3 = route_query("Compara los modelos de razonamiento frente a los LLMs tradicionales")
    assert d3.intencion == "pregunta_abierta"
    assert d3.nivel == "T1"

    # Pregunta T0 determinista tradicional debe permanecer en T0
    d4 = route_query("¿Cuáles son los temas en tendencia?")
    assert d4.intencion == "temas_en_tendencia"
    assert d4.nivel == "T0"


def test_retrieve_relevant_cards(db_with_cards):
    """Debe recuperar las tarjetas semánticamente afines y extraer las fuentes."""
    cards, sources = retrieve_relevant_cards(
        "¿Cómo funciona la seguridad y sandboxing en agentes?",
        db=db_with_cards,
        top_k=2,
    )
    assert len(cards) >= 1
    assert "Sandboxing" in cards[0]["texto"]
    assert "https://github.com/aws-safebox/aws-safebox" in sources


def test_deterministic_open_fallback():
    """El fallback determinista debe sintetizar una respuesta estructurada."""
    cards = [
        {"texto": "Sandboxing de Agentes | fase: emergente | gancho dominante: tutorial | fuentes: GitHub"},
    ]
    resp = _deterministic_open_fallback("¿Cómo proteger agentes?", cards, ["https://github.com/aws-safebox"])
    assert "### 💡 Análisis Estratégico Sonar" in resp
    assert "Sandboxing de Agentes" in resp
    assert "Recomendaciones para Directivos" in resp


def test_answer_open_question_contract(db_with_cards):
    """Debe respetar el contrato de respuesta estructurada."""
    result = answer_open_question(
        "¿Cuál es la estrategia recomendada para reducir costos de IA en LatAm?",
        db=db_with_cards,
        force_level="T1",
    )
    assert "respuesta" in result
    assert result["intencion"] == "pregunta_abierta"
    assert "latencia_ms" in result
    assert result["latencia_ms"] >= 0
    assert "modelo" in result
    assert isinstance(result["fuentes"], list)


def test_chatservice_open_question_flow(db_with_cards):
    """El servicio ChatService debe resolver preguntas abiertas y persistir logs."""
    service = ChatService(db=db_with_cards)
    res = service.ask(
        "¿Qué recomendaciones tienes para implementar modelos de razonamiento?",
        no_cache=True,
    )
    assert res["intencion"] == "pregunta_abierta"
    assert len(res["respuesta"]) > 50

    # Comprobar que se guardó en chat_logs
    logs = db_with_cards.get_chat_logs(limit=10)
    assert len(logs) >= 1
    assert logs[0]["intencion"] == "pregunta_abierta"
