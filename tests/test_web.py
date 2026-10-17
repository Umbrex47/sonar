"""Pruebas unitarias para la interfaz web y API de Radar30X."""

import json
from http.server import ThreadingHTTPServer
import threading
import httpx
import pytest

from web.server import (
    RadarHTTPHandler,
    list_available_reports,
    load_latest_report,
    query_db_items,
    enrich_report_references,
)


def test_list_available_reports():
    reports = list_available_reports()
    assert isinstance(reports, list)
    if reports:
        assert "filename" in reports[0]
        assert "semana" in reports[0]


def test_load_latest_report():
    data = load_latest_report()
    if data:
        assert "semana" in data
        assert "top_temas" in data
        assert len(data["top_temas"]) > 0
        first_topic = data["top_temas"][0]
        assert "referencias_detalladas" in first_topic
        for ref in first_topic["referencias_detalladas"]:
            assert "url" in ref
            assert "fuente" in ref
            assert "titulo" in ref


def test_enrich_report_references_fallback():
    mock_report = {
        "semana": "2026-W42",
        "top_temas": [
            {
                "tema": "Tema de prueba",
                "evidencia": ["https://techcrunch.com/2026/10/16/custom-article-slug"],
            }
        ],
    }
    enriched = enrich_report_references(mock_report)
    ref = enriched["top_temas"][0]["referencias_detalladas"][0]
    assert ref["url"] == "https://techcrunch.com/2026/10/16/custom-article-slug"
    assert "techcrunch" in ref["fuente"].lower() or "techcrunch" in ref["autor"].lower()


def test_query_db_items():
    items = query_db_items(limit=10)
    assert isinstance(items, list)
    if items:
        assert "fuente" in items[0]
        assert "titulo" in items[0]
        assert "url" in items[0]


def test_web_server_endpoints():
    """Inicia un servidor web en un puerto efímero y verifica los endpoints HTTP."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), RadarHTTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"

    try:
        with httpx.Client(base_url=base_url, timeout=5.0, trust_env=False) as client:
            # 1. Dashboard HTML
            res_html = client.get("/")
            assert res_html.status_code == 200
            assert "Radar de Contenido 30X" in res_html.text

            # 2. API Reports
            res_rep = client.get("/api/reports")
            assert res_rep.status_code == 200
            rep_json = res_rep.json()
            assert "reports" in rep_json

            # 3. API Latest Report
            res_latest = client.get("/api/report/latest")
            assert res_latest.status_code in [200, 404]
            if res_latest.status_code == 200:
                data = res_latest.json()
                assert "top_temas" in data

            # 4. API Items
            res_items = client.get("/api/items?limit=5")
            assert res_items.status_code == 200
            items_json = res_items.json()
            assert "items" in items_json

            # 5. API Status
            res_status = client.get("/api/status")
            assert res_status.status_code == 200
            status_json = res_status.json()
            assert "is_running" in status_json
    finally:
        server.shutdown()
        server.server_close()
