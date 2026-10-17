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

            # 6. API Focuses
            res_foc = client.get("/api/focuses")
            assert res_foc.status_code == 200
            foc_json = res_foc.json()
            assert "focuses" in foc_json
            assert len(foc_json["focuses"]) >= 4

            # 7. Add Focus
            new_f_payload = {
                "nombre": "Test Focus",
                "categoria": "polemicas",
                "keywords": ["test1", "test2"],
                "descripcion": "Descripción de prueba",
            }
            res_add = client.post("/api/focuses", json=new_f_payload)
            assert res_add.status_code == 201
            created = res_add.json()["focus"]
            assert created["nombre"] == "Test Focus"
            f_id = created["id"]

            # 8. Toggle Focus
            res_tog = client.post(f"/api/focuses/{f_id}/toggle")
            assert res_tog.status_code == 200
            assert res_tog.json()["focus"]["activo"] is False

            # 9. Delete Focus
            res_del = client.delete(f"/api/focuses/{f_id}")
            assert res_del.status_code == 200
            assert res_del.json()["status"] == "deleted"

            # 10. API Knowledge - List
            res_knw = client.get("/api/knowledge")
            assert res_knw.status_code == 200
            assert "sources" in res_knw.json()

            # 11. API Knowledge - Ingest
            knw_payload = {
                "url": "https://www.youtube.com/watch?v=knwtest12345",
                "solicitud": "Extraer ganchos contraintuitivos",
                "titulo": "Agentes y Liderazgo",
                "tipo": "youtube",
            }
            res_ing = client.post("/api/knowledge/ingest", json=knw_payload)
            assert res_ing.status_code == 201
            ing_data = res_ing.json()
            assert ing_data["status"] == "success"
            knw_id = ing_data["source"]["id"]

            # 12. API Knowledge - Search
            res_search = client.post("/api/knowledge/search", json={"query": "agentes liderazgo", "top_k": 2})
            assert res_search.status_code == 200
            assert "results" in res_search.json()

            # 13. API Knowledge - Delete
            res_del_knw = client.delete(f"/api/knowledge/{knw_id}")
            assert res_del_knw.status_code == 200
            assert res_del_knw.json()["status"] == "deleted"
    finally:
        server.shutdown()
        server.server_close()
