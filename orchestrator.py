"""Orquestador central para la arquitectura de agentes de Radar30X.

Coordina el ciclo de 12 horas idempotente y el proceso de backfill histórico:
1. Agente Explorador: barre fuentes públicas y deduplica.
2. Agrupamiento temático: clustering determinista con rapidfuzz.
3. Agente Historiador: memoria vectorial de 90 días, cálculo de novedad y fases.
4. Agente Crítico: auditoría empírica, veracidad y filtro anti-humo sin alucinación.
5. Calibrador y Ranking: decisiones con TypeSafe Jev y generación del reporte final.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from agents.base import AgentResult, Narrative, RunContext, Verdict
from agents.critic import CriticAgent
from agents.explorer import ExplorerAgent
from agents.historian import HistorianAgent
from pipeline.db import Database
from pipeline.decide import ClusterDecision, decide_cluster
from pipeline.knowledge.vector_store import VectorStore
from pipeline.scoring import ScoredTopic, partition_topics_funnel, rank_topics
from pipeline.topics import TopicCluster, cluster_items
from sources.github import GitHubSource
from sources.hackernews import HackerNewsSource

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orquestador multi-agente con memoria narrativa y trazabilidad total."""

    def __init__(
        self,
        db: Optional[Database] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        self.db = db or Database()
        self.vector_store = vector_store or VectorStore()

    def run_cycle(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ejecuta un ciclo completo de 12 horas con los 3 agentes y ranking final."""
        cycle_start = time.time()
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        logger.info("=== [ORQUESTADOR] Iniciando Ciclo Multi-Agente (run_id=%s) ===", run_id)

        self.db.start_run(run_id=run_id, kind="cycle")
        ctx = RunContext(run_id=run_id, db=self.db, kind="cycle", config=config or {})

        agent_results: Dict[str, AgentResult] = {}

        try:
            # 1. Agente Explorador
            explorer = ExplorerAgent()
            res_explorer = explorer.run(ctx)
            agent_results[explorer.name] = res_explorer

            # 2. Agrupamiento temático (Clustering)
            clusters = cluster_items(ctx.items, similarity_threshold=75.0)
            ctx.clusters = clusters
            logger.info("[ORQUESTADOR] %d clusters temáticos detectados.", len(clusters))

            # 3. Agente Historiador (Memoria 90d + Novedad + Fases)
            historian = HistorianAgent(vector_store=self.vector_store)
            res_historian = historian.run(ctx)
            agent_results[historian.name] = res_historian

            # 4. Agente Crítico (Auditoría de Veracidad + Anti-Humo)
            critic = CriticAgent()
            res_critic = critic.run(ctx)
            agent_results[critic.name] = res_critic

            # 5. Decisiones con Jev y Ranking Ponderado
            logger.info("[ORQUESTADOR] Calibrando decisiones Jev y ranking final...")
            decisions: List[ClusterDecision] = []
            for cl in ctx.clusters:
                dec = decide_cluster(cl)
                # Enriquecer con veredicto del Crítico si existe
                verdict = ctx.verdicts.get(cl.cluster_id)
                if verdict and dec.audit:
                    if verdict.veredicto == "descartado":
                        dec.audit.veredicto = "DESCARTADO"
                        dec.audit.motivo_veredicto = f"Descartado por Crítico: {'; '.join(verdict.razones)}"
                    elif verdict.veredicto == "dudoso" and dec.audit.veredicto == "APROBADO":
                        dec.audit.veredicto = "EN_OBSERVACION"
                        dec.audit.motivo_veredicto = f"En observación por Crítico: {'; '.join(verdict.razones)}"
                decisions.append(dec)

            ranked_topics = rank_topics(ctx.clusters, decisions)
            top_10 = ranked_topics[:10]

            # Construir reporte JSON enriquecido con métricas de agentes
            now_iso = datetime.now(timezone.utc).isoformat()
            semana = datetime.now(timezone.utc).strftime("%Y-W%W")
            aprobados, en_obs, descartados = partition_topics_funnel(ranked_topics, top_n=10)

            report_data = {
                "semana": semana,
                "generado": now_iso,
                "run_id": run_id,
                "total_clusters_evaluados": len(ranked_topics),
                "embudo_metricas": {
                    "total_evaluados": len(ranked_topics),
                    "aprobados_top": len(top_10),
                    "en_observacion": len(en_obs),
                    "descartados": len(descartados),
                },
                "top_temas": [
                    {
                        "posicion": idx,
                        "tema": t.cluster.tema_canonico,
                        "fase": t.decision.fase,
                        "confianza_jev": t.decision.confianza,
                        "crecimiento": t.crecimiento_label,
                        "score": round(t.score, 3),
                        "fuentes": t.cluster.fuentes,
                        "gancho": t.decision.gancho,
                        "formato": t.decision.formato,
                        "encaje_audiencia": t.decision.encaje_audiencia,
                        "por_que": getattr(t.decision, "por_que", None) or "Validado por el sistema multi-agente con memoria narrativa.",
                        "por_que_audiencia": getattr(t.decision, "por_que_audiencia", None) or getattr(t.decision, "adaptacion_30x", None) or "Relevante para líderes y directores en LatAm.",
                        "adaptacion_30x": getattr(t.decision, "adaptacion_30x", None) or "Formato recomendado para la audiencia 30X.",
                        "evidencia": [it.url for it in t.cluster.items[:3]],
                        "sparkline": next((n.sparkline for n in ctx.narratives if n.id == t.cluster.cluster_id), ".:oO*"),
                        "novedad": next((n.novelty for n in ctx.narratives if n.id == t.cluster.cluster_id), 1.0),
                        "veredicto_critico": (
                            ctx.verdicts[t.cluster.cluster_id].model_dump() if t.cluster.cluster_id in ctx.verdicts else None
                        ),
                        "proceso_decision": t.decision.audit.model_dump() if t.decision.audit else None,
                    }
                    for idx, t in enumerate(top_10, 1)
                ],
                "temas_en_observacion": [
                    {
                        "tema": t.cluster.tema_canonico,
                        "fuentes": t.cluster.fuentes,
                        "score": round(t.score, 3),
                        "motivo": "En lista de espera",
                        "veredicto": "EN_OBSERVACION",
                        "evidencia": [it.url for it in t.cluster.items[:3]],
                    }
                    for t in en_obs[:25]
                ],
                "temas_descartados": [
                    {"tema": t.cluster.tema_canonico, "score": round(t.score, 3), "motivo": "Descartado"}
                    for t in descartados[:25]
                ],
            }

            # Guardar reporte en base de datos y disco
            self.db.save_report(report_id=f"rep_{semana}", semana=semana, payload=report_data)
            out_dir = os.environ.get("RADAR_OUT_DIR") or os.path.join(os.path.dirname(__file__), "out")
            report_file = ""
            try:
                os.makedirs(out_dir, exist_ok=True)
                report_file = os.path.join(out_dir, f"report_{semana}.json")
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
            except OSError as ex:
                logger.warning("No se pudo escribir archivo de reporte en disco (%s): %s", out_dir, ex)

            # Materializar tarjetas de narrativa para el Chatbot RAG
            try:
                from pipeline.cards import materialize_all_narrative_cards
                cards_count = materialize_all_narrative_cards(db=self.db, vector_store=self.vector_store, report_data=report_data)
                logger.info("[ORQUESTADOR] %d tarjetas de narrativa materializadas para RAG.", cards_count)
            except Exception as ex:
                logger.warning("[ORQUESTADOR] No se pudieron materializar tarjetas de narrativa: %s", ex)

            elapsed_total_ms = (time.time() - cycle_start) * 1000

            run_stats = {
                "elapsed_ms": round(elapsed_total_ms, 1),
                "items_recolectados": len(ctx.items),
                "clusters_formados": len(ctx.clusters),
                "narrativas_analizadas": len(ctx.narratives),
                "top_temas_aprobados": len(top_10),
                "report_file": report_file,
            }

            self.db.finish_run(run_id=run_id, status="completed", stats=run_stats)
            logger.info("=== [ORQUESTADOR] Ciclo Completado con Éxito (%.1f ms) ===", elapsed_total_ms)

            return {
                "ok": True,
                "run_id": run_id,
                "stats": run_stats,
                "report_file": report_file,
                "top_10": report_data["top_temas"],
            }

        except Exception as exc:
            logger.exception("[ORQUESTADOR] Error crítico en ciclo: %s", exc)
            self.db.finish_run(run_id=run_id, status="failed", stats={"error": str(exc)})
            return {"ok": False, "run_id": run_id, "error": str(exc)}

    def run_backfill(self, days: int = 90, limit_per_slice: int = 30) -> Dict[str, Any]:
        """Puebla la memoria histórica de 90 días consultando HackerNews y GitHub por tramos temporales.
        
        Resuelve el riesgo crítico de Cold Start: sin pasado, todo se clasificaría como Emergente.
        """
        backfill_start = time.time()
        run_id = f"backfill_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        logger.info("=== [ORQUESTADOR] Iniciando Backfill Histórico de %d Días (run_id=%s) ===", days, run_id)

        self.db.start_run(run_id=run_id, kind="backfill")
        hn_source = HackerNewsSource()
        gh_source = GitHubSource()

        now = datetime.now(timezone.utc)
        total_backfilled = 0
        slices_count = days // 7

        all_historical_items = []

        # Recorrer tramos de 7 días hacia atrás
        for i in range(slices_count):
            start_dt = now - timedelta(days=(i + 1) * 7)
            end_dt = now - timedelta(days=i * 7)

            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())

            start_str = start_dt.strftime("%Y-%m-%d")
            end_str = end_dt.strftime("%Y-%m-%d")

            logger.info("[BACKFILL] Tramo %d/%d: %s a %s...", i + 1, slices_count, start_str, end_str)

            # 1. Hacker News Algolia por ventana
            try:
                hn_items = hn_source.fetch_window(start_ts=start_ts, end_ts=end_ts, limit=limit_per_slice)
                all_historical_items.extend(hn_items)
            except Exception as e:
                logger.warning("[BACKFILL] Error en HN tramo %d: %s", i, e)

            # 2. GitHub Search por ventana
            try:
                gh_items = gh_source.fetch_window(start_date=start_str, end_date=end_str, limit=limit_per_slice // 2)
                all_historical_items.extend(gh_items)
            except Exception as e:
                logger.warning("[BACKFILL] Error en GitHub tramo %d: %s", i, e)

        # Deduplicar e insertar en base de datos
        from pipeline.normalize import normalize_and_deduplicate
        unique_historical = normalize_and_deduplicate(all_historical_items)
        inserted = self.db.save_items(unique_historical, run_id=run_id)

        # Indexar embeddings para la memoria vectorial
        logger.info("[BACKFILL] Indexando %d vectores en la memoria vectorial...", len(unique_historical))
        for it in unique_historical[:300]:
            text = f"{it.titulo} | {it.resumen}"
            vec = self.vector_store.generate_embedding(text)
            blob = VectorStore.pack_embedding(vec)
            self.db.save_item_embedding(item_id=it.id, vector_blob=blob, dim=len(vec))

        elapsed_ms = (time.time() - backfill_start) * 1000
        stats = {
            "dias_cubiertos": days,
            "tramos_procesados": slices_count,
            "total_recolectados": len(all_historical_items),
            "unicos_guardados": inserted,
            "elapsed_ms": round(elapsed_ms, 1),
        }

        self.db.finish_run(run_id=run_id, status="completed", stats=stats)
        self.db.log_audit(
            run_id=run_id,
            agente="Orquestador",
            accion="backfill_completado",
            payload=stats,
        )

        logger.info("=== [ORQUESTADOR] Backfill completado: %d ítems guardados en %.1f ms ===", inserted, elapsed_ms)
        return {"ok": True, "run_id": run_id, "stats": stats}
