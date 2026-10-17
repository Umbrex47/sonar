"""Pruebas unitarias para las nuevas fuentes de datos (HuggingFace y Newsletters)."""

from sources.huggingface import HuggingFaceSource
from sources.newsletters import NewslettersSource


def test_huggingface_source_initialization():
    hf = HuggingFaceSource()
    assert hf.name == "HuggingFace"
    assert "trending" in hf.TRENDING_MODELS_URL
    assert "daily_papers" in hf.DAILY_PAPERS_URL


def test_newsletters_source_initialization():
    nl = NewslettersSource()
    assert nl.name == "Newsletters"
    assert len(nl.FEEDS) >= 3
    # Comprobar que los feeds incluyen The Rundown AI y Startups LatAm
    feed_names = [f[0] for f in nl.FEEDS]
    assert "The Rundown AI" in feed_names
    assert "Startups LatAm" in feed_names


def test_huggingface_fetch_structure():
    hf = HuggingFaceSource(timeout=10.0)
    items = hf.fetch(limit=10)
    # Si hay conexión a internet debe traer ítems válidos
    if items:
        first = items[0]
        assert first.fuente == "HuggingFace"
        assert len(first.titulo) > 5
        assert first.url.startswith("https://huggingface.co/")
        assert "interacciones_totales" in first.metricas
