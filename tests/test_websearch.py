"""Pruebas unitarias para el motor de búsqueda web automatizado (WebSearchSource)."""

import os
import pytest
from unittest.mock import patch, MagicMock

from sources.websearch import (
    WebSearchSource,
    search_duckduckgo_html,
    search_web_engine,
    _clean_html,
    _extract_domain,
)
from sources.base import RawItem
from pipeline.normalize import normalize_and_deduplicate


def test_clean_html():
    raw = "<b>OpenAI</b> &amp; <i>Anthropic</i> debate &#39;safety&#39;"
    cleaned = _clean_html(raw)
    assert "<b>" not in cleaned
    assert "<i>" not in cleaned
    assert "OpenAI & Anthropic debate 'safety'" in cleaned


def test_extract_domain():
    assert _extract_domain("https://techcrunch.com/2026/01/ai-agents") == "Techcrunch.com"
    assert _extract_domain("https://www.reuters.com/technology") == "Reuters.com"
    assert _extract_domain("not-a-valid-url") == "Web"


def test_search_web_engine_fallback_or_live():
    # Ejecutar búsqueda para un término clave
    items = search_web_engine("DeepSeek R1 benchmarks razonamiento", limit=4)
    assert len(items) > 0
    for it in items:
        assert isinstance(it, RawItem)
        assert it.fuente == "WebSearch"
        assert len(it.titulo) > 0
        assert len(it.url) > 0
        assert it.metricas.get("es_busqueda_web") == 1


def test_websearch_source_queries_integration():
    source = WebSearchSource()
    queries = source._get_queries()
    assert len(queries) >= 3
    # Debe contener queries temáticas
    queries_text = " ".join(queries).lower()
    assert any(term in queries_text for term in ["openai", "anthropic", "agentes", "ia"])


def test_websearch_source_fetch():
    source = WebSearchSource(timeout=10.0)
    limit = 6
    items = source.fetch(limit=limit)
    assert isinstance(items, list)
    assert len(items) <= limit
    assert len(items) > 0
    for it in items:
        assert it.fuente == "WebSearch"
        assert it.url.startswith("http")


def test_websearch_normalization_and_deduplication():
    item1 = RawItem(
        id="w1",
        fuente="WebSearch",
        titulo="Anthropic presenta nuevo modelo para razonamiento empresarial",
        resumen="Análisis sobre costo y eficiencia",
        url="https://tech.example.com/anthropic-model?utm_source=duckduckgo&ref=web",
        autor="Tech.example.com",
        fecha="2026-10-17T10:00:00Z",
    )
    item2 = RawItem(
        id="w2",
        fuente="WebSearch",
        titulo="Anthropic presenta nuevo modelo para razonamiento empresarial",
        resumen="Análisis sobre costo y eficiencia",
        url="https://tech.example.com/anthropic-model",
        autor="Tech.example.com",
        fecha="2026-10-17T10:00:00Z",
    )
    # Deduplicar
    deduped = normalize_and_deduplicate([item1, item2])
    assert len(deduped) == 1
    assert "utm_source" not in deduped[0].url
