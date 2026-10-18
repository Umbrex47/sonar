"""Pruebas unitarias para la materialización de tarjetas de narrativa (cards.py)."""

import os
import tempfile
import pytest

from pipeline.cards import format_narrative_card, materialize_all_narrative_cards
from pipeline.db import Database
from pipeline.knowledge.vector_store import VectorStore


def test_format_narrative_card():
    card_text = format_narrative_card(
        narrative_id="test_narrative_1",
        tema="Modelos de Razonamiento Cuantizados",
        fase="emergente",
        first_seen="2026-W42",
        pico_fecha=None,
        semanas_desde_pico=0,
        fuentes=["HackerNews", "GitHub"],
        gancho="contraintuitivo",
        formato="video_corto",
        veredicto="valido",
        veracidad_p=0.88,
        humo_p=0.08,
        novedad=0.92,
        ratio_copias=0.1,
        sparkline=".:oO*",
        por_que="Reducción drástica de VRAM en inferencia local.",
        adaptacion_30x="Short explicando cómo correr modelos 8B en laptops de $800.",
        evidencias=["https://github.com/test/repo", "https://news.ycombinator.com/item?id=123"],
    )

    assert "Modelos de Razonamiento Cuantizados" in card_text
    assert "fase: emergente" in card_text
    assert "gancho dominante: contraintuitivo" in card_text
    assert "veredicto: valido" in card_text
    assert "veracidad: 88%" in card_text
    assert "novedad: 92%" in card_text
    assert "sparkline: [.:oO*]" in card_text
    assert "https://github.com/test/repo" in card_text


def test_materialize_all_narrative_cards(tmp_path):
    db_file = str(tmp_path / "test_cards.db")
    db = Database(db_path=db_file)
    vector_store = VectorStore(db_path=db_file)

    # Insertar reporte de prueba
    report_data = {
        "semana": "2026-W42",
        "top_temas": [
            {
                "posicion": 1,
                "tema": "Sandboxing para Agentes de IA",
                "fase": "naciendo",
                "crecimiento": "+120%",
                "confianza_jev": 0.85,
                "fuentes": ["GitHub", "HackerNews"],
                "gancho": "tutorial",
                "formato": "video_corto",
                "por_que": "Aislamiento de comandos no autorizados.",
                "adaptacion_30x": "Carrusel de ciberseguridad.",
                "evidencia": ["https://github.com/safebox/test"],
                "sparkline": ".:oO*",
                "novedad": 0.95,
                "veredicto_critico": {
                    "veredicto": "valido",
                    "veracidad_p": 0.90,
                    "humo_p": 0.05,
                },
            }
        ],
    }

    count = materialize_all_narrative_cards(db=db, vector_store=vector_store, report_data=report_data)
    assert count >= 1

    cards = db.get_all_narrative_cards()
    assert len(cards) >= 1
    assert "Sandboxing para Agentes de IA" in cards[0]["texto"]
    assert cards[0]["embedding"] is not None
