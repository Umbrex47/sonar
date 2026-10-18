"""Pruebas unitarias y de integración para el Orquestador del sistema de agentes."""

import tempfile
import pytest

from agents.base import RawItem
from orchestrator import Orchestrator
from pipeline.db import Database


def test_orchestrator_initialization():
    """Verifica que el Orquestador inicialice sus componentes correctamente."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db = Database(db_path=tmp.name)
        orch = Orchestrator(db=db)
        assert orch.db is not None
        assert orch.vector_store is not None


def test_orchestrator_run_cycle_end_to_end(monkeypatch):
    """Verifica la ejecución completa de un ciclo multi-agente."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db = Database(db_path=tmp.name)

        # Sembrar 2 ítems iniciales
        db.save_items([
            RawItem(
                id="it_1",
                fuente="HackerNews",
                titulo="Anthropic releases Model Context Protocol for enterprise agents",
                resumen="Open standard for connecting AI models to data",
                url="https://anthropic.com/news/mcp",
                autor="Anthropic",
                fecha="2026-10-16T12:00:00Z",
                metricas={"puntos": 450, "comentarios": 180},
            ),
            RawItem(
                id="it_2",
                fuente="GitHub",
                titulo="Anthropic MCP official SDK and tools",
                resumen="Official Python SDK for MCP",
                url="https://github.com/modelcontextprotocol/python-sdk",
                autor="modelcontextprotocol",
                fecha="2026-10-16T13:00:00Z",
                metricas={"estrellas": 1200},
            ),
        ])

        orch = Orchestrator(db=db)

        # Mock del explorer para que use los ítems ya sembrados
        from agents.explorer import ExplorerAgent

        def mock_explorer_run(self, ctx):
            from agents.base import AgentResult
            ctx.items = ctx.db.get_all_items()
            return AgentResult(ok=True, agent_name=self.name, items=ctx.items)

        monkeypatch.setattr(ExplorerAgent, "run", mock_explorer_run)

        res = orch.run_cycle()

        assert res["ok"] is True
        assert "run_id" in res
        assert "top_10" in res
        assert len(res["top_10"]) >= 1

        # Verificar que el run quedó completado en la BD
        runs = db.get_runs(limit=5)
        assert len(runs) >= 1
        assert runs[0]["status"] == "completed"
        assert runs[0]["kind"] == "cycle"

        # Verificar registros de auditoría
        audit_entries = db.get_audit_logs(run_id=res["run_id"])
        assert len(audit_entries) >= 2


def test_orchestrator_run_backfill(monkeypatch):
    """Verifica la ejecución del backfill histórico contra cold start."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db = Database(db_path=tmp.name)
        orch = Orchestrator(db=db)

        # Mock de las llamadas externas de backfill
        from sources.hackernews import HackerNewsSource
        from sources.github import GitHubSource

        def mock_hn_fetch_window(self, start_ts, end_ts, limit=40):
            return [
                RawItem(
                    id=f"hn_hist_{start_ts}",
                    fuente="HackerNews",
                    titulo="Autonomous Agents Benchmark Evaluation 2026",
                    resumen="Comparative benchmark of agent frameworks",
                    url=f"https://news.ycombinator.com/item?id={start_ts}",
                    autor="researcher",
                    fecha="2026-08-15T10:00:00Z",
                    metricas={"puntos": 150},
                )
            ]

        def mock_gh_fetch_window(self, start_date, end_date, limit=25):
            return [
                RawItem(
                    id=f"gh_hist_{start_date}",
                    fuente="GitHub",
                    titulo="AgentFramework/memory-store",
                    resumen="Vector memory repository",
                    url=f"https://github.com/agentframework/memory-{start_date}",
                    autor="dev",
                    fecha=f"{start_date}T10:00:00Z",
                    metricas={"estrellas": 90},
                )
            ]

        monkeypatch.setattr(HackerNewsSource, "fetch_window", mock_hn_fetch_window)
        monkeypatch.setattr(GitHubSource, "fetch_window", mock_gh_fetch_window)

        res = orch.run_backfill(days=14, limit_per_slice=10)

        assert res["ok"] is True
        assert res["stats"]["dias_cubiertos"] == 14
        assert res["stats"]["unicos_guardados"] > 0

        # Verificar que el run de backfill quedó registrado
        runs = db.get_runs(limit=5)
        backfill_run = next(r for r in runs if r["kind"] == "backfill")
        assert backfill_run["status"] == "completed"
