"""Agente Explorador (ExplorerAgent) para Radar30X.

Responsabilidad: Barrer fuentes públicas configuradas, extraer publicaciones,
deduplicar por URL canónica y persistir los ítems crudos asociados al run activo.
"""

from datetime import datetime, timezone
import logging
import time
from typing import List, Optional

from agents.base import AgentResult, RunContext
from sources import get_default_sources
from sources.base import BaseSource, RawItem
from pipeline.normalize import normalize_and_deduplicate

logger = logging.getLogger(__name__)


class ExplorerAgent:
    """Agente responsable del descubrimiento e ingesta de fuentes públicas."""

    name: str = "Explorador"

    def __init__(self, sources: Optional[List[BaseSource]] = None) -> None:
        self.sources = sources or get_default_sources(include_optional=True)

    def run(self, ctx: RunContext) -> AgentResult:
        """Ejecuta la recolección multi-fuente y actualiza el contexto del run."""
        start_time = time.time()
        logger.info("[%s] Iniciando barrido de fuentes públicas (run_id=%s)...", self.name, ctx.run_id)

        all_items: List[RawItem] = []
        fuentes_stats = {}
        errors = []

        for src in self.sources:
            try:
                logger.debug("[%s] Conectando a %s...", self.name, src.name)
                limit = ctx.config.get("limit_per_source", 35)
                fetched = src.fetch(limit=limit)
                all_items.extend(fetched)
                fuentes_stats[src.name] = len(fetched)
                logger.info("[%s] %s: %d ítems obtenidos.", self.name, src.name, len(fetched))
            except Exception as exc:
                err_msg = f"Error en fuente {src.name}: {exc}"
                logger.warning("[%s] %s", self.name, err_msg)
                errors.append(err_msg)
                fuentes_stats[src.name] = 0

        # Deduplicación canónica
        unique_items = normalize_and_deduplicate(all_items)
        dedup_count = len(all_items) - len(unique_items)

        # Persistencia en base de datos con vinculación a run_id
        inserted = ctx.db.save_items(unique_items, run_id=ctx.run_id)

        elapsed_ms = (time.time() - start_time) * 1000
        metrics = {
            "total_recolectados": len(all_items),
            "unicos_deduplicados": len(unique_items),
            "duplicados_descartados": dedup_count,
            "nuevos_insertados": inserted,
            "desglose_fuentes": fuentes_stats,
            "fuentes_consultadas": len(self.sources),
        }

        # Registro en el log de auditoría
        ctx.db.log_audit(
            run_id=ctx.run_id,
            agente=self.name,
            accion="barrido_completado",
            payload=metrics,
        )

        ctx.items = unique_items

        logger.info(
            "[%s] Finalizado: %d ítems únicos listos para análisis histórico (%.1f ms).",
            self.name,
            len(unique_items),
            elapsed_ms,
        )

        return AgentResult(
            ok=len(unique_items) > 0,
            agent_name=self.name,
            items=unique_items,
            metrics=metrics,
            errors=errors,
            execution_time_ms=elapsed_ms,
        )
