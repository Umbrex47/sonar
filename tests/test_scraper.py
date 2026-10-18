"""Pruebas unitarias para el motor de Scraping Híbrido y Seguro de Sonar."""

import pytest
from unittest.mock import MagicMock, patch

from pipeline.scraper import HybridScraper, ScrapeResult


def test_scraper_status_contract():
    scraper = HybridScraper()
    status = scraper.get_status()
    assert "motores" in status
    assert "jina_reader" in status["motores"]
    assert "direct_stealth" in status["motores"]
    assert status["motores"]["jina_reader"]["costo"] == "$0.00"
    assert status["seguridad"]["ssrf_protection"] is True


def test_ssrf_protection():
    scraper = HybridScraper()
    
    # Intento de acceso a localhost
    safe, err = scraper.validate_url("http://localhost:8080/admin")
    assert safe is False
    assert "loopback" in err.lower() or "localhost" in err.lower()

    # Intento de acceso a 127.0.0.1
    safe, err = scraper.validate_url("http://127.0.0.1/secrets")
    assert safe is False

    # Intento de esquema peligroso
    safe, err = scraper.validate_url("file:///etc/passwd")
    assert safe is False

    # URL pública válida
    safe, err = scraper.validate_url("https://techcrunch.com/2026/10/16/ai-agent-breakthrough")
    assert safe is True
    assert err is None


def test_stealth_headers():
    scraper = HybridScraper()
    headers = scraper._get_stealth_headers()
    assert "User-Agent" in headers
    assert "Sec-Fetch-Dest" in headers
    assert "Mozilla/5.0" in headers["User-Agent"]


def test_direct_stealth_html_parsing():
    html_sample = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>DeepSeek R1 Architecture Review</title>
        <meta name="author" content="Dr. Elena Vance" />
        <meta property="article:published_time" content="2026-10-15T12:00:00Z" />
      </head>
      <body>
        <nav><a href="/">Home</a></nav>
        <article>
          <h1>DeepSeek R1 Architecture Review</h1>
          <p>Los modelos de razonamiento destilados han demostrado paridad empírica con arquitecturas propietarias.</p>
          <h2>Eficiencia de Inferencia</h2>
          <p>El costo de cómputo se redujo en un 80% comparado con la generación anterior.</p>
          <ul>
            <li>Paridad de razonamiento en código</li>
            <li>Inferencia local en hardware accesible</li>
          </ul>
        </article>
        <footer>Copyright 2026</footer>
      </body>
    </html>
    """
    scraper = HybridScraper()
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_sample
        mock_get.return_value = mock_resp

        res = scraper.scrape_stealth("https://tech-insider.org/deepseek-review")
        assert res is not None
        assert res.status == "success"
        assert res.method_used == "direct_stealth"
        assert res.cost_estimate == "$0.00"
        assert "DeepSeek R1 Architecture Review" in res.title
        assert res.author == "Dr. Elena Vance"
        assert "Paridad de razonamiento en código" in res.content_markdown
        # Verificar que el nav y footer fueron eliminados
        assert "Home" not in res.content_markdown
        assert "Copyright" not in res.content_markdown


def test_jina_reader_parsing():
    jina_markdown_sample = """
Title: Anthropic Claude 3.7 Hybrid Reasoning
Author: Tech Analyst
Published Date: 2026-10-14

# Anthropic Claude 3.7 Hybrid Reasoning

Anthropic ha introducido su nuevo modelo con control granular de tiempo de pensamiento.

### Puntos clave para CTOs:
- Permite fijar un presupuesto exacto de tokens de razonamiento.
- Reduce latencia innecesaria en consultas factuales simples.
"""
    scraper = HybridScraper()
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = jina_markdown_sample
        mock_get.return_value = mock_resp

        res = scraper.scrape_jina("https://ai-news.com/claude-37")
        assert res is not None
        assert res.status == "success"
        assert res.method_used == "jina_reader"
        assert res.cost_estimate == "$0.00"
        assert res.title == "Anthropic Claude 3.7 Hybrid Reasoning"
        assert res.author == "Tech Analyst"
        assert "control granular de tiempo de pensamiento" in res.content_markdown


def test_zenrows_fallback_when_blocked():
    scraper = HybridScraper(zenrows_api_key="zr_test_key_12345")
    
    with patch.object(scraper, "scrape_jina", return_value=None), \
         patch.object(scraper, "scrape_stealth", return_value=None), \
         patch.object(scraper, "scrape_zenrows") as mock_zen:
        
        mock_zen.return_value = ScrapeResult(
            url="https://protected-site.com/report",
            status="success",
            title="Protected Report",
            content_markdown="# Protected Report\nContenido rescatado por ZenRows",
            content_text="Contenido rescatado por ZenRows",
            method_used="zenrows",
            cost_estimate="~$0.002",
            domain="protected-site.com",
        )

        res = scraper.scrape("https://protected-site.com/report", mode="auto")
        assert res.status == "success"
        assert res.method_used == "zenrows"
        assert res.cost_estimate == "~$0.002"
        mock_zen.assert_called_once()


def test_google_news_url_resolution():
    scraper = HybridScraper()
    mock_html = '<div data-n-a-sg="sig_abc123" data-n-a-ts="1710000000"></div>'
    mock_batch_resp = ')]}\'\n[["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://www.canonical-news.org/article-1\\"]"]]'

    with patch("httpx.Client.get") as mock_get, patch("httpx.Client.post") as mock_post:
        resp_get = MagicMock()
        resp_get.status_code = 200
        resp_get.text = mock_html
        mock_get.return_value = resp_get

        resp_post = MagicMock()
        resp_post.status_code = 200
        resp_post.text = mock_batch_resp
        mock_post.return_value = resp_post

        resolved = scraper.resolve_google_news_url("https://news.google.com/rss/articles/CBMiFakeArticleId123?oc=5")
        assert resolved == "https://www.canonical-news.org/article-1"


def test_hybrid_scraper_search_web():
    scraper = HybridScraper(zenrows_api_key="zr_test")
    rss_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Google News</title>
        <item>
          <title>Agentes de IA en Finanzas 2026</title>
          <link>https://news.google.com/rss/articles/CBMiTest123</link>
          <description>&lt;b&gt;Bancos adoptan IA&lt;/b&gt; para operaciones seguras.</description>
          <pubDate>Sun, 18 Oct 2026 10:00:00 GMT</pubDate>
          <source url="https://fintech.com">Fintech Insider</source>
        </item>
      </channel>
    </rss>
    """

    with patch("httpx.Client.get") as mock_get, \
         patch.object(scraper, "resolve_google_news_url", return_value="https://fintech.com/agentes-2026"), \
         patch.object(scraper, "scrape") as mock_scrape:

        resp = MagicMock()
        resp.status_code = 200
        resp.content = rss_sample.encode("utf-8")
        resp.text = rss_sample
        mock_get.return_value = resp

        mock_scrape.return_value = ScrapeResult(
            url="https://fintech.com/agentes-2026",
            status="success",
            title="Agentes de IA en Finanzas 2026",
            content_markdown="# Agentes de IA en Finanzas 2026\nTexto completo extraído por Jina",
            content_text="Texto completo extraído por Jina",
            method_used="jina_reader",
            cost_estimate="$0.00",
            domain="fintech.com",
            tokens_estimate=520,
        )

        results = scraper.search_web("agentes finanzas 2026", limit=5, enrich_top_k=1)
        assert len(results) > 0
        first = results[0]
        assert first.engine == "google_news"
        assert first.title == "Agentes de IA en Finanzas 2026"
        assert first.url == "https://fintech.com/agentes-2026"
        assert first.enriched is True
        assert first.tokens_estimate == 520


