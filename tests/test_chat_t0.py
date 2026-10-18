"""Pruebas unitarias para el Chatbot RAG nivel T0 y router (chat/t0_deterministic.py, chat/router.py)."""

import pytest

from chat.router import compute_query_hash, route_query
from chat.service import ChatService
from chat.t0_deterministic import execute_t0_query
from pipeline.db import Database


def test_router_intent_classification():
    # 1. Temas en tendencia y ganchos
    d1 = route_query("¿Cuáles son los temas en tendencia y qué ganchos están usando?")
    assert d1.intencion == "temas_en_tendencia"
    assert d1.nivel == "T0"
    assert not d1.fuera_de_alcance

    # 2. Solo ganchos
    d2 = route_query("¿Qué ganchos psicológicos tienen mayor retención?")
    assert d2.intencion == "ganchos_usados"

    # 3. Saturación
    d3 = route_query("¿Qué temas están saturados o quemados?")
    assert d3.intencion == "que_esta_saturado"

    # 4. Novedades por fuente
    d4 = route_query("¿Qué novedades de IA salieron en HackerNews y GitHub?")
    assert d4.intencion == "novedades_por_fuente"

    # 5. Evolución
    d5 = route_query("Dime la evolución histórica y trayectoria de los agentes")
    assert d5.intencion == "evolucion_de_tema"

    # 6. Veredicto del crítico
    d6 = route_query("¿Cuál es el veredicto del crítico y la veracidad?")
    assert d6.intencion == "veredicto_de_tema"

    # 7. Fuera de alcance
    d7 = route_query("¿Cuál es la capital de Francia y qué tiempo hace?")
    assert d7.fuera_de_alcance
    assert d7.intencion == "fuera_de_alcance"


def test_t0_execution_all_intents(tmp_path):
    db_file = str(tmp_path / "test_chat.db")
    db = Database(db_path=db_file)

    report_data = {
        "semana": "2026-W42",
        "top_temas": [
            {
                "posicion": 1,
                "tema": "Model Context Protocol en Producción",
                "fase": "naciendo",
                "crecimiento": "+150%",
                "confianza_jev": 0.9,
                "fuentes": ["GitHub", "HackerNews"],
                "gancho": "tutorial",
                "formato": "video_corto",
                "por_que": "Interoperabilidad estandarizada de herramientas para agentes.",
                "adaptacion_30x": "Tutorial de 60s para conectar herramientas a Claude.",
                "evidencia": ["https://github.com/modelcontextprotocol/servers"],
                "sparkline": ".:oO*",
                "novedad": 0.9,
                "veredicto_critico": {
                    "veredicto": "valido",
                    "veracidad_p": 0.92,
                    "impacto_real": 0.85,
                    "humo_p": 0.05,
                    "tiene_fuente_primaria": True,
                    "razones": ["Validado en repositorio oficial."],
                },
            }
        ],
    }
    db.save_report(report_id="rep_2026-W42", semana="2026-W42", payload=report_data)

    # 1. Consulta temas en tendencia
    res1 = execute_t0_query("temas_en_tendencia", "¿Cuáles son los temas en tendencia?", db=db)
    assert res1["nivel"] == "T0"
    assert "Model Context Protocol" in res1["respuesta"]
    assert len(res1["fuentes"]) >= 1

    # 2. Consulta ganchos
    res2 = execute_t0_query("ganchos_usados", "¿Qué ganchos usan?", db=db)
    assert "TUTORIAL" in res2["respuesta"]

    # 3. Consulta saturación
    res3 = execute_t0_query("que_esta_saturado", "¿Qué está saturado?", db=db)
    assert "no se detectan temas saturados" in res3["respuesta"].lower()

    # 4. Consulta evolución
    res4 = execute_t0_query("evolucion_de_tema", "Evolución de Model Context Protocol", db=db)
    assert "Model Context Protocol" in res4["respuesta"]
    assert ".:oO*" in res4["respuesta"]

    # 5. Consulta veredicto
    res5 = execute_t0_query("veredicto_de_tema", "Veredicto sobre Model Context Protocol", db=db)
    assert "VALIDO" in res5["respuesta"]
    assert "92%" in res5["respuesta"]


def test_chat_service_caching_and_observability(tmp_path):
    db_file = str(tmp_path / "test_service.db")
    db = Database(db_path=db_file)
    service = ChatService(db=db)

    # Primera consulta (calculada)
    q = "¿Cuáles son los temas en tendencia y qué ganchos están usando?"
    res_first = service.ask(q, no_cache=False)
    assert res_first["nivel"] == "T0"
    assert not res_first.get("desde_cache")

    # Segunda consulta idéntica (debe venir de caché)
    res_second = service.ask(q, no_cache=False)
    assert res_second.get("desde_cache") is True

    # Verificar que se registró en chat_logs
    logs = db.get_chat_logs()
    assert len(logs) >= 1
    assert logs[0]["pregunta"] == q
    assert logs[0]["nivel"] == "T0"
