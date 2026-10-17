"""Pruebas unitarias para normalización, deduplicación y agrupamiento temático."""

from sources.base import RawItem
from pipeline.normalize import canonicalize_url, normalize_and_deduplicate
from pipeline.topics import clean_topic_phrase, cluster_items


def test_canonicalize_url():
    dirty_url = "https://example.com/blog/ai-agent?utm_source=twitter&utm_medium=social&ref=feed"
    clean = canonicalize_url(dirty_url)
    assert "utm_source" not in clean
    assert "ref" not in clean
    assert clean == "https://example.com/blog/ai-agent"


def test_clean_topic_phrase():
    title = "Show HN: LocalAgent v2 [Tutorial] #Shorts"
    cleaned = clean_topic_phrase(title)
    assert "Show HN:" not in cleaned
    assert "[Tutorial]" not in cleaned
    assert "#Shorts" not in cleaned
    assert "LocalAgent v2" in cleaned


def test_normalize_and_deduplicate():
    items = [
        RawItem(
            id="1",
            fuente="HN",
            titulo="Agentes de Inteligencia Artificial en Producción",
            url="https://example.com/post1?utm_campaign=launch",
        ),
        RawItem(
            id="2",
            fuente="Reddit",
            titulo="Agentes de Inteligencia Artificial en Produccion",
            url="https://example.com/post1?utm_source=reddit",
        ),
        RawItem(
            id="3",
            fuente="Medium",
            titulo="Un tema completamente diferente sobre Bases de Datos",
            url="https://example.com/databases",
        ),
    ]
    unique = normalize_and_deduplicate(items)
    # Post 1 y 2 tienen la misma URL canónica y títulos casi idénticos
    assert len(unique) == 2


def test_cluster_items():
    items = [
        RawItem(
            id="1",
            fuente="YouTube",
            titulo="Agentes de IA con memoria persistente",
            url="https://yt.com/1",
            metricas={"vistas_por_hora": 450.0},
        ),
        RawItem(
            id="2",
            fuente="HackerNews",
            titulo="Agentes de IA y memoria persistente local",
            url="https://hn.com/2",
            metricas={"puntos": 230},
        ),
        RawItem(
            id="3",
            fuente="GoogleNews",
            titulo="Nueva ley de ciberseguridad en el sector bancario",
            url="https://news.com/3",
            metricas={"relevancia": 1.0},
        ),
    ]
    clusters = cluster_items(items, similarity_threshold=70.0)
    # Debe haber 2 clusters: uno para memoria persistente y otro para ley bancaria
    assert len(clusters) == 2
    mem_cluster = next(c for c in clusters if "memoria" in c.tema_canonico.lower())
    assert len(mem_cluster.items) == 2
    assert "YouTube" in mem_cluster.fuentes
    assert "HackerNews" in mem_cluster.fuentes
