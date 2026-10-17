"""Pruebas unitarias para el motor de decisiones Jev y calibración de salida."""

from pipeline.decide import ClusterDecision, _heuristic_calibrate
from pipeline.topics import TopicCluster
from sources.base import RawItem


def test_cluster_decision_validation():
    dec = ClusterDecision(
        fase="naciendo",
        gancho="dato_contraintuitivo",
        formato="video_corto",
        novedad=0.91,
        encaje_audiencia=0.88,
        confianza=0.93,
    )
    assert dec.fase == "naciendo"
    assert dec.gancho == "dato_contraintuitivo"
    assert 0.0 <= dec.novedad <= 1.0
    assert 0.0 <= dec.encaje_audiencia <= 1.0


def test_heuristic_calibrate_fast_short():
    cluster = TopicCluster(
        cluster_id="test1",
        tema_canonico="Agentes de IA con memoria persistente",
        items=[
            RawItem(
                id="1",
                fuente="YouTube",
                titulo="Demostré en 45 segundos cómo conectar memoria a agentes",
                url="https://example.com/yt1",
                metricas={"vistas_por_hora": 480.0, "formato": "video_corto"},
            )
        ],
        fuentes=["YouTube"],
        total_menciones=1,
        metricas_agregadas={"max_vistas_por_hora": 480.0, "total_items": 1},
    )
    dec = _heuristic_calibrate(cluster)
    assert dec.fase == "naciendo"
    assert dec.formato == "video_corto"
    assert dec.novedad >= 0.8
    assert dec.confianza >= 0.75
