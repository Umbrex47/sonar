"""Pruebas unitarias para los adaptadores de fuentes en Radar30X."""

import os
from sources.base import RawItem
from sources.manual import ManualCSVSource
from sources.youtube import YouTubeSource


def test_raw_item_creation():
    item = RawItem(
        id="test-123",
        fuente="HackerNews",
        titulo="Agentes autónomos en producción",
        url="https://news.ycombinator.com/item?id=123",
        metricas={"puntos": 150, "comentarios": 45},
    )
    assert item.id == "test-123"
    assert item.fuente == "HackerNews"
    assert item.get_metric("puntos") == 150.0
    assert item.get_metric("inexistente", 10.0) == 10.0


def test_manual_csv_source():
    # El archivo data/manual.csv debe existir y contener datos
    src = ManualCSVSource(file_path="data/manual.csv")
    items = src.fetch(limit=10)
    assert len(items) >= 4
    first = items[0]
    assert first.fuente.startswith("LinkedIn") or "Manual" in first.fuente
    assert "url" in first.model_dump()
    assert first.get_metric("interacciones_totales") > 0


def test_youtube_duration_parser():
    yt = YouTubeSource(api_key=None)
    assert yt._parse_iso_duration_seconds("PT45S") == 45
    assert yt._parse_iso_duration_seconds("PT2M10S") == 130
    assert yt._parse_iso_duration_seconds("PT1H5M") == 3900


def test_youtube_views_per_hour():
    yt = YouTubeSource(api_key=None)
    # Si se publicó hace tiempo o tiene vistas, debe retornar float > 0
    vph = yt._calculate_views_per_hour(1000, "2026-10-15T12:00:00Z")
    assert vph > 0.0
