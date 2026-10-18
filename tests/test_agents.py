"""Pruebas unitarias para la arquitectura de agentes (Explorador, Historiador, Crítico)."""

import tempfile
import pytest

from agents.base import AgentResult, Narrative, RunContext, Verdict
from agents.critic import CriticAgent, _evaluate_critic_signals, _calibrate_critic_deterministic
from agents.explorer import ExplorerAgent
from agents.historian import HistorianAgent, cosine_sim, generate_sparkline
from pipeline.db import Database
from pipeline.topics import TopicCluster
from sources.base import BaseSource, RawItem


class DummySource(BaseSource):
    name = "Dummy"

    def fetch(self, limit: int = 10):
        return [
            RawItem(
                id="d1",
                fuente="Dummy",
                titulo="OpenAI lanza o3 con razonamiento avanzado",
                resumen="Anuncio oficial de nuevo modelo de frontera",
                url="https://openai.com/index/o3",
                autor="OpenAI",
                fecha="2026-10-15T10:00:00Z",
                metricas={"puntos": 350, "comentarios": 120},
            ),
            RawItem(
                id="d2",
                fuente="Dummy",
                titulo="OpenAI lanza o3 con razonamiento avanzado",  # Duplicado para dedup
                resumen="Anuncio idéntico",
                url="https://openai.com/index/o3",
                autor="OpenAI",
                fecha="2026-10-15T10:00:00Z",
                metricas={"puntos": 350, "comentarios": 120},
            ),
        ]


def test_agent_contracts_and_models():
    """Verifica que los modelos Narrative y Verdict cumplan sus restricciones."""
    n = Narrative(
        id="narr_1",
        tema="Agentes con memoria persistente",
        items=[],
        first_seen="2026-10-01",
        last_seen="2026-10-17",
        fase="emergente",
        novelty=0.85,
        recurrencia=2,
        pico_fecha="2026-10-15",
        semanas_desde_pico=0,
        ratio_copias=0.10,
        fuentes_distintas=3,
        sparkline=".:oO*",
    )
    assert n.fase == "emergente"
    assert n.novelty == 0.85
    assert n.sparkline == ".:oO*"

    v = Verdict(
        narrative_id="narr_1",
        veracidad_p=0.92,
        impacto_real=0.88,
        humo_p=0.08,
        veredicto="valido",
        razones=["Respaldado por repo oficial", "3 fuentes independientes"],
    )
    assert v.veredicto == "valido"
    assert v.humo_p == 0.08


def test_explorer_agent_ingestion_and_dedup():
    """Verifica que ExplorerAgent procese fuentes, deduplique y registre auditoría."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db = Database(db_path=tmp.name)
        ctx = RunContext(run_id="run_test_01", db=db)

        explorer = ExplorerAgent(sources=[DummySource()])
        res = explorer.run(ctx)

        assert res.ok is True
        assert res.metrics["total_recolectados"] == 2
        assert res.metrics["unicos_deduplicados"] == 1
        assert res.metrics["duplicados_descartados"] == 1
        assert len(ctx.items) == 1

        # Verificar auditoría persistida
        logs = db.get_audit_logs(run_id="run_test_01", agente="Explorador")
        assert len(logs) == 1
        assert logs[0]["accion"] == "barrido_completado"


def test_historian_sparkline_and_evolution():
    """Verifica el cálculo de sparkline, similitud coseno y clasificación del Historiador."""
    # Prueba del generador de sparkline
    spark = generate_sparkline([0, 2, 5, 10, 25, 40])
    assert len(spark) == 6
    assert spark.startswith(".")
    assert spark.endswith("*")

    # Prueba de similitud coseno
    sim_identical = cosine_sim([1.0, 0.0, 0.5], [1.0, 0.0, 0.5])
    assert pytest.approx(sim_identical, 0.001) == 1.0

    sim_orthogonal = cosine_sim([1.0, 0.0], [0.0, 1.0])
    assert pytest.approx(sim_orthogonal, 0.001) == 0.0

    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db = Database(db_path=tmp.name)
        ctx = RunContext(run_id="run_test_hist", db=db)

        item = RawItem(
            id="h1",
            fuente="HackerNews",
            titulo="Sandboxing and Security for Autonomous Agents",
            resumen="Security framework for agents",
            url="https://github.com/aws/safebox",
            autor="aws",
            fecha="2026-10-16T12:00:00Z",
            metricas={"puntos": 200},
        )
        ctx.items = [item]

        historian = HistorianAgent()
        res = historian.run(ctx)

        assert res.ok is True
        assert len(ctx.narratives) == 1
        narrative = ctx.narratives[0]
        assert narrative.fase in ["emergente", "crecimiento", "saturado", "resurgente"]
        assert 0.0 <= narrative.novelty <= 1.0
        assert len(narrative.sparkline) > 0


def test_critic_agent_auditing_and_anti_smoke():
    """Verifica que el Crítico detecte fuentes primarias, castigue clickbait y emita veredicto."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db = Database(db_path=tmp.name)
        ctx = RunContext(run_id="run_test_crit", db=db)

        # Narrativa de alta calidad con repo oficial en GitHub
        valid_item = RawItem(
            id="v1",
            fuente="GitHub",
            titulo="LangChain releases memory engine for agent persistence",
            resumen="Framework for enterprise workflows with benchmarks",
            url="https://github.com/langchain-ai/langchain",
            autor="hwchase17",
            fecha="2026-10-16T12:00:00Z",
            metricas={"estrellas": 500},
        )
        valid_narrative = Narrative(
            id="cl_valid",
            tema="LangChain Memory Engine",
            items=[valid_item],
            first_seen="2026-10-10",
            last_seen="2026-10-16",
            fase="emergente",
            novelty=0.85,
            recurrencia=2,
            fuentes_distintas=2,
            sparkline="..:o*",
        )

        # Narrativa sensacionalista / clickbait
        clickbait_item = RawItem(
            id="cb1",
            fuente="Web",
            titulo="¡NO VAS A CREER cómo esta herramienta DESTRUYE a los programadores!",
            resumen="Curiosidad sin código ni fuentes",
            url="https://clickbait-news.net/secret123",
            autor="anon",
            fecha="2026-10-16T12:00:00Z",
            metricas={"vistas": 50},
        )
        cb_narrative = Narrative(
            id="cl_cb",
            tema="Herramienta destruye programadores",
            items=[clickbait_item],
            first_seen="2026-10-16",
            last_seen="2026-10-16",
            fase="saturado",
            novelty=0.10,
            recurrencia=1,
            fuentes_distintas=1,
            sparkline="*",
        )

        ctx.narratives = [valid_narrative, cb_narrative]

        critic = CriticAgent()
        res = critic.run(ctx)

        assert res.ok is True
        assert len(ctx.verdicts) == 2

        v_valid = ctx.verdicts["cl_valid"]
        v_cb = ctx.verdicts["cl_cb"]

        # El válido debe tener fuente primaria y bajo humo
        assert v_valid.tiene_fuente_primaria is True
        assert v_valid.humo_p < 0.40

        # El clickbait debe ser penalizado con alto humo
        assert v_cb.penalidad_clickbait > 0.0
        assert v_cb.humo_p > v_valid.humo_p
        assert v_cb.veredicto in ["descartado", "dudoso"]
