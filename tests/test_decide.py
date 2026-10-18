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
    assert dec.audit is not None
    assert len(dec.audit.preguntas) == 5
    assert dec.audit.veredicto in ("APROBADO", "EN_OBSERVACION", "DESCARTADO")
    assert len(dec.audit.motivo_veredicto) > 10


def test_audit_trail_toy_project_discarded():
    cluster = TopicCluster(
        cluster_id="toy1",
        tema_canonico="Calorie tracker rewrite one turn",
        items=[
            RawItem(
                id="toy-1",
                fuente="HackerNews",
                titulo="Calorie tracker rewrite one turn with AI",
                url="https://example.com/hn1",
            )
        ],
        fuentes=["HackerNews"],
        total_menciones=1,
    )
    dec = _heuristic_calibrate(cluster)
    assert dec.audit is not None
    assert dec.audit.veredicto == "DESCARTADO"
    assert "juguete" in dec.audit.motivo_veredicto.lower()


def test_decision_cache():
    from pipeline.decide import decide_cluster, clear_decision_cache, _DECISION_CACHE
    clear_decision_cache()
    cluster = TopicCluster(
        cluster_id="cache-1",
        tema_canonico="Modelos de razonamiento en producción",
        items=[
            RawItem(
                id="c-1",
                fuente="WebSearch",
                titulo="Modelos de razonamiento en producción para empresas",
                url="https://example.com/cache1",
            )
        ],
        fuentes=["WebSearch"],
        total_menciones=1,
    )
    dec1 = decide_cluster(cluster)
    assert len(_DECISION_CACHE) == 1
    dec2 = decide_cluster(cluster)
    assert dec1 is dec2  # Idéntica referencia desde caché
    clear_decision_cache()
    assert len(_DECISION_CACHE) == 0

