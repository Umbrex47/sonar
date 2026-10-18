"""Pruebas unitarias para la interfaz web y API de Radar30X."""

import json
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from unittest.mock import patch
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


def test_web_server_endpoints(monkeypatch, tmp_path):
    """Inicia un servidor web en un puerto efímero y verifica los endpoints HTTP."""
    test_db = str(tmp_path / "web_test.db")
    monkeypatch.setenv("RADAR_DB_PATH", test_db)

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
            assert "Sonar" in res_html.text

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

            # 14. API RSS.app - List
            res_rss = client.get("/api/rssapp/feeds")
            assert res_rss.status_code == 200
            assert "feeds" in res_rss.json()

            # 15. API RSS.app - Create
            res_rss_add = client.post("/api/rssapp/feeds", json={
                "url": "https://rss.app/feeds/test_feed.xml",
                "nombre": "Test RSS.app Feed",
                "plataforma": "Twitter/X",
                "enfoque_id": "polemicas-labs",
            })
            assert res_rss_add.status_code == 201
            rss_feed_id = res_rss_add.json()["feed"]["id"]

            # 16. API RSS.app - Toggle
            res_rss_tog = client.post(f"/api/rssapp/feeds/{rss_feed_id}/toggle")
            assert res_rss_tog.status_code == 200
            assert res_rss_tog.json()["feed"]["activo"] is False

            # 17. API RSS.app - Delete
            res_rss_del = client.delete(f"/api/rssapp/feeds/{rss_feed_id}")
            assert res_rss_del.status_code == 200
            assert res_rss_del.json()["status"] == "deleted"

            # 18. API Chatbot - Ask
            res_chat = client.post("/api/chat/ask", json={
                "pregunta": "¿Cuáles son los temas en tendencia?",
                "show_sources": True,
            })
            assert res_chat.status_code == 200
            chat_data = res_chat.json()
            assert "respuesta" in chat_data
            assert chat_data["nivel"] == "T0"

            # 19. API Chatbot - Logs
            res_logs = client.get("/api/chat/logs")
            assert res_logs.status_code == 200
            assert "logs" in res_logs.json()

            # 20. API Drafts - Create
            res_draft_create = client.post("/api/drafts", json={
                "titulo": "Borrador API Test",
                "formato": "video_corto",
                "gancho": "opinion",
            })
            assert res_draft_create.status_code == 201
            d_id = res_draft_create.json()["id"]

            # 21. API Drafts - List
            res_draft_list = client.get("/api/drafts")
            assert res_draft_list.status_code == 200
            assert any(d["id"] == d_id for d in res_draft_list.json()["drafts"])

            # 22. API Drafts - Detail
            res_draft_get = client.get(f"/api/drafts/{d_id}")
            assert res_draft_get.status_code == 200
            assert res_draft_get.json()["titulo"] == "Borrador API Test"

            # 23. API Drafts - Update Status
            res_draft_status = client.post(f"/api/drafts/{d_id}/status", json={"estado": "en_revision"})
            assert res_draft_status.status_code == 200
            assert res_draft_status.json()["nuevo_estado"] == "en_revision"

            # 24. API Scraper - Status
            res_scraper_status = client.get("/api/scraper/status")
            assert res_scraper_status.status_code == 200
            scraper_data = res_scraper_status.json()
            assert "motores" in scraper_data
            assert "jina_reader" in scraper_data["motores"]

            # 25. API Scraper - Extract (SSRF safety check)
            res_scraper_ssrf = client.post("/api/scraper/extract", json={"url": "http://127.0.0.1/secrets"})
            assert res_scraper_ssrf.status_code == 200
            assert res_scraper_ssrf.json()["status"] == "error"
            assert "seguridad" in res_scraper_ssrf.json()["title"].lower()

            # 26. API WebSearch - GET test
            from sources.base import RawItem
            mock_items = [
                RawItem(
                    id="mock_ws_1",
                    fuente="WebSearch",
                    titulo="OpenAI Enterprise Agent Benchmark",
                    url="https://openai.com/blog/benchmark",
                    resumen="Resultados de pruebas con agentes autónomos.",
                    fecha_publicacion=datetime.now(timezone.utc),
                    score_relevancia=0.85,
                    metadatos={"query": "OpenAI"},
                )
            ]
            with patch("sources.websearch.search_web_engine", return_value=mock_items):
                res_ws_get = client.get("/api/websearch/test?q=OpenAI")
                assert res_ws_get.status_code == 200
                assert "results" in res_ws_get.json()

                # 27. API WebSearch - POST query with alias
                res_ws_post = client.post("/api/websearch/query", json={"q": "OpenAI"})
                assert res_ws_post.status_code == 200
                assert "results" in res_ws_post.json()

            # 28. API Playground Eval - with headline
            res_play = client.post("/api/playground/eval", json={
                "headline": "DeepSeek R1 benchmarks",
                "fuentes": ["HackerNews"],
                "vistas_por_hora": 150.0,
            })
            assert res_play.status_code == 200
            play_data = res_play.json()
            assert play_data["tema"] == "DeepSeek R1 benchmarks"
            assert "decision" in play_data
            assert "score_final" in play_data
    finally:
        server.shutdown()
        server.server_close()
