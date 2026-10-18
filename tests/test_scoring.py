"""Pruebas unitarias para scoring ponderado y ranking de temas."""

from pipeline.decide import ClusterDecision
from pipeline.scoring import calculate_topic_score, rank_topics
from pipeline.topics import TopicCluster
from sources.base import RawItem


def test_calculate_topic_score():
    cluster = TopicCluster(
        cluster_id="c1",
        tema_canonico="Agentes de IA para directivos",
        items=[
            RawItem(id="1", fuente="YouTube", titulo="Demo", url="https://yt.com/1"),
            RawItem(id="2", fuente="HackerNews", titulo="Demo HN", url="https://hn.com/2"),
        ],
        fuentes=["YouTube", "HackerNews"],
        metricas_agregadas={"max_vistas_por_hora": 450.0, "total_items": 2},
    )
    decision = ClusterDecision(
        fase="naciendo",
        gancho="dato_contraintuitivo",
        formato="video_corto",
        novedad=0.90,
        encaje_audiencia=0.92,
        confianza=0.88,
    )

    score, label = calculate_topic_score(cluster, decision)
    assert score > 0.5
    assert "+" in label
    assert "%" in label


def test_rank_topics_ordering():
    c1 = TopicCluster(
        cluster_id="c1",
        tema_canonico="Tema de alto crecimiento",
        items=[RawItem(id="1", fuente="HN", titulo="T1", url="https://hn.com/1")],
        fuentes=["HN", "YouTube", "GitHub"],
        metricas_agregadas={"max_vistas_por_hora": 600.0, "total_items": 5},
    )
    d1 = ClusterDecision(
        fase="naciendo",
        gancho="contraste",
        formato="video_corto",
        novedad=0.95,
        encaje_audiencia=0.95,
        confianza=0.90,
    )

    c2 = TopicCluster(
        cluster_id="c2",
        tema_canonico="Tema saturado y viejo",
        items=[RawItem(id="2", fuente="Medium", titulo="T2", url="https://m.com/2")],
        fuentes=["Medium"],
        metricas_agregadas={"max_vistas_por_hora": 10.0, "total_items": 1},
    )
    d2 = ClusterDecision(
        fase="saturado",
        gancho="opinion",
        formato="articulo",
        novedad=0.20,
        encaje_audiencia=0.40,
        confianza=0.80,
    )

    ranked = rank_topics([c2, c1], [d2, d1])
    assert len(ranked) == 2
    assert ranked[0].cluster.cluster_id == "c1"
    assert ranked[0].score > ranked[1].score


def test_partition_topics_funnel():
    from pipeline.decide import DecisionAuditTrail
    from pipeline.scoring import partition_topics_funnel

    c1 = TopicCluster(cluster_id="c1", tema_canonico="Aprobado", items=[], fuentes=["YouTube"])
    d1 = ClusterDecision(
        fase="naciendo", gancho="contraste", formato="video_corto", novedad=0.9, encaje_audiencia=0.9, confianza=0.9,
        audit=DecisionAuditTrail(veredicto="APROBADO", motivo_veredicto="Aprobado Top 10")
    )

    c2 = TopicCluster(cluster_id="c2", tema_canonico="Juguete", items=[], fuentes=["HN"])
    d2 = ClusterDecision(
        fase="naciendo", gancho="opinion", formato="articulo", novedad=0.5, encaje_audiencia=0.3, confianza=0.8,
        audit=DecisionAuditTrail(veredicto="DESCARTADO", motivo_veredicto="Descartado: Proyecto de juguete")
    )

    c3 = TopicCluster(cluster_id="c3", tema_canonico="Observado", items=[], fuentes=["GitHub"])
    d3 = ClusterDecision(
        fase="naciendo", gancho="tutorial", formato="hilo", novedad=0.8, encaje_audiencia=0.7, confianza=0.8,
        audit=DecisionAuditTrail(veredicto="EN_OBSERVACION", motivo_veredicto="En Observación: 1 sola fuente")
    )

    ranked = rank_topics([c1, c2, c3], [d1, d2, d3])
    aprobados, observacion, descartados = partition_topics_funnel(ranked, top_n=1)

    assert len(aprobados) == 1
    assert aprobados[0].cluster.cluster_id == "c1"
    assert len(descartados) == 1
    assert descartados[0].cluster.cluster_id == "c2"
    assert len(observacion) == 1
    assert observacion[0].cluster.cluster_id == "c3"

