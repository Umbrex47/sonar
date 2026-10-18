"""Pruebas unitarias para la integración de RSS.app (gestor y adaptador de fuentes)."""

import json
from unittest.mock import MagicMock, patch
import pytest

from pipeline.rssapp_manager import (
    RSSAppFeed,
    load_rssapp_feeds,
    save_rssapp_feeds,
    add_rssapp_feed,
    toggle_rssapp_feed,
    delete_rssapp_feed,
    verify_rssapp_feed_connection,
)
from sources.rssapp import RSSAppSource, clean_social_text


def test_clean_social_text():
    raw = "Sam Altman anuncia o3 https://t.co/xyz #AI pic.twitter.com/abc #OpenAI"
    cleaned = clean_social_text(raw)
    assert "https://" not in cleaned
    assert "pic.twitter.com" not in cleaned
    assert "#AI" not in cleaned
    assert "Sam Altman anuncia o3" in cleaned


def test_rssapp_manager_crud(tmp_path, monkeypatch):
    test_file = tmp_path / "test_rssapp_feeds.json"
    monkeypatch.setattr("pipeline.rssapp_manager.DATA_FILE", test_file)
    monkeypatch.setattr("pipeline.rssapp_manager._IN_MEMORY_FEEDS", None)

    # 1. Cargar inicial (crea los defaults)
    feeds = load_rssapp_feeds(force_reload=True)
    assert len(feeds) >= 3

    # 2. Agregar nuevo feed
    new_feed = add_rssapp_feed(
        url="https://rss.app/feeds/custom_twitter.xml",
        nombre="X Tech Founders",
        plataforma="Twitter/X",
        enfoque_id="polemicas-labs",
    )
    assert new_feed.nombre == "X Tech Founders"
    assert new_feed.plataforma == "Twitter/X"

    # 3. Toggle
    toggled = toggle_rssapp_feed(new_feed.id)
    assert toggled is not None
    assert toggled.activo is False

    # 4. Delete
    deleted = delete_rssapp_feed(new_feed.id)
    assert deleted is True

    feeds_after = load_rssapp_feeds()
    assert not any(f.id == new_feed.id for f in feeds_after)


def test_rssapp_source_parse_xml(tmp_path, monkeypatch):
    test_file = tmp_path / "test_rssapp_feeds.json"
    monkeypatch.setattr("pipeline.rssapp_manager.DATA_FILE", test_file)

    feed = RSSAppFeed(
        id="rssapp-mock",
        nombre="TikTok IA Viral",
        url="https://rss.app/feeds/mock_tiktok.xml",
        plataforma="TikTok",
        enfoque_id="agentes-operaciones",
        activo=True,
    )
    save_rssapp_feeds([feed])

    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>TikTok IA Viral</title>
        <link>https://tiktok.com/@ia</link>
        <description>Tendencias de IA</description>
        <item>
          <title>Agente autónomo reemplaza 5 horas de prospección diaria</title>
          <link>https://tiktok.com/@ia/video/123456</link>
          <description>Tutorial práctico para directores de ventas #ia #automation</description>
          <pubDate>Fri, 17 Oct 2026 10:00:00 GMT</pubDate>
          <author>@creator</author>
        </item>
      </channel>
    </rss>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_xml.encode("utf-8")
    mock_resp.json.side_effect = Exception("Not JSON")

    source = RSSAppSource()
    with patch("httpx.Client.get", return_value=mock_resp):
        items = source.fetch(limit=10)

    assert len(items) == 1
    assert items[0].fuente == "RSS.app (TikTok)"
    assert "Agente autónomo" in items[0].titulo
    assert items[0].metricas["formato"] == "video_corto"
    assert items[0].metricas["plataforma"] == "TikTok"


def test_test_rssapp_feed_helper():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Sam Altman X Feed",
        "items": [
            {"title": "Working on reasoning models", "url": "https://x.com/sama/status/1", "date_published": "2026-10-17T09:00:00Z"}
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        res = verify_rssapp_feed_connection("https://rss.app/feeds/sample.json")

    assert res["ok"] is True
    assert res["tipo"] == "JSON Feed"
    assert len(res["muestra"]) == 1
    assert res["muestra"][0]["titulo"] == "Working on reasoning models"
