"""Agente Crítico / Auditor (CriticAgent) para Radar30X.

Responsabilidad: Auditar la veracidad, corroboración empírica y nivel de "humo" de cada narrativa.
Regla de oro: Nunca afirma un hecho ni usa conocimiento libre del LLM como verdad.
Solo evalúa si la evidencia concreta y las señales verificables aportadas respaldan el tema.
"""

from datetime import datetime, timezone
import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agents.base import AgentResult, Narrative, RunContext, Verdict

logger = logging.getLogger(__name__)

# Dominios considerados de alta reputación o fuentes primarias
PRIMARY_DOMAINS = [
    "arxiv.org",
    "github.com",
    "gitlab.com",
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "huggingface.co",
    "reuters.com",
    "nature.com",
    "technologyreview.com",
    "techcrunch.com",
    "bloomberg.com",
]

# Patrones regex de títulos bomba / clickbait / sensacionalismo
CLICKBAIT_PATTERNS = [
    re.compile(r"no vas a creer", re.I),
    re.compile(r"el fin de", re.I),
    re.compile(r"the end of", re.I),
    re.compile(r"destruye a", re.I),
    re.compile(r"game over", re.I),
    re.compile(r"shocking", re.I),
    re.compile(r"10x your", re.I),
    re.compile(r"will replace all", re.I),
    re.compile(r"morirá", re.I),
    re.compile(r"\b(secret|secreto)s?\b", re.I),
    re.compile(r"!{2,}"),
]


class CriticSchema(BaseModel):
    """Esquema de salida estructurado para la evaluación con Jev."""

    veracidad_p: float = Field(ge=0.0, le=1.0)
    impacto_real: float = Field(ge=0.0, le=1.0)
    humo_p: float = Field(ge=0.0, le=1.0)
    veredicto: str  # "valido" | "dudoso" | "descartado"


def _evaluate_critic_signals(
    narrative: Narrative,
) -> Dict[str, Any]:
    """Extrae señales objetivas de corroboración, fuentes primarias y clickbait."""
    items = narrative.items
    urls = [it.url for it in items]
    titles = [it.titulo for it in items]
    fuentes = list(set(it.fuente for it in items))

    # 1. Corroboración por fuentes independientes
    n_fuentes = len(fuentes)

    # 2. Detección de fuentes primarias / dominios de reputación
    has_primary = False
    reputable_count = 0
    for u in urls:
        u_lower = u.lower()
        if any(dom in u_lower for dom in PRIMARY_DOMAINS):
            has_primary = True
            reputable_count += 1

    # 3. Detector de clickbait
    clickbait_matches = []
    for t in titles:
        for pat in CLICKBAIT_PATTERNS:
            if pat.search(t):
                clickbait_matches.append(t)
                break

    ratio_clickbait = len(clickbait_matches) / len(titles) if titles else 0.0

    # 4. Magnitud y tracción
    total_interactions = 0
    for it in items:
        m = it.metricas or {}
        total_interactions += (
            int(m.get("puntos", 0))
            + int(m.get("vistas", 0))
            + int(m.get("estrellas", 0))
            + int(m.get("interacciones_totales", 0))
        )

    return {
        "n_fuentes": n_fuentes,
        "fuentes": fuentes,
        "has_primary": has_primary,
        "reputable_count": reputable_count,
        "ratio_clickbait": ratio_clickbait,
        "total_interactions": total_interactions,
    }


def _calibrate_critic_deterministic(signals: Dict[str, Any], narrative: Narrative) -> Verdict:
    """Evaluación calibrada basada en reglas y probabilidades deterministas (RLCD)."""
    n_fuentes = signals["n_fuentes"]
    has_primary = signals["has_primary"]
    ratio_cb = signals["ratio_clickbait"]

    razones = []

    # Cálculo de veracidad base
    if n_fuentes >= 3:
        veracidad_base = 0.88
        razones.append(f"Corroborado en {n_fuentes} fuentes independientes ({', '.join(signals['fuentes'])}).")
    elif n_fuentes == 2:
        veracidad_base = 0.72
        razones.append(f"Validación cruzada en 2 fuentes distintas ({', '.join(signals['fuentes'])}).")
    else:
        veracidad_base = 0.45
        razones.append(f"Reportado en 1 sola fuente ({signals['fuentes'][0] if signals['fuentes'] else 'desconocida'}); requiere reserva.")

    if has_primary:
        veracidad_base = min(1.0, veracidad_base + 0.10)
        razones.append("Enlaza fuente primaria o repositorio de código oficial verificado.")
    else:
        veracidad_base = max(0.20, veracidad_base - 0.08)

    # Cálculo de humo
    humo_p = 0.10
    if ratio_cb > 0.30:
        humo_p += 0.35
        razones.append(f"Detectados patrones de titular sensacionalista o clickbait en {int(ratio_cb*100)}% de las piezas.")
    if not has_primary and n_fuentes == 1:
        humo_p += 0.30
        razones.append("Falta de respaldo empírico o paper oficial.")
    if narrative.fase == "saturado":
        humo_p += 0.15
        razones.append(f"Narrativa saturada con {int(narrative.ratio_copias*100)}% de copias casi idénticas.")

    humo_p = round(max(0.02, min(0.98, humo_p)), 2)
    veracidad_p = round(max(0.05, min(0.99, veracidad_base - (humo_p * 0.3))), 2)

    # Impacto real para empresas
    title_corpus = " ".join([narrative.tema] + [it.titulo for it in narrative.items]).lower()
    has_enterprise = any(
        k in title_corpus
        for k in ["costo", "operacion", "banca", "fintech", "seguridad", "roi", "empresa", "produccion", "rpa", "compliance", "ceo", "liderazgo"]
    )
    is_toy = any(k in title_corpus for k in ["toy project", "calorie tracker", "fake photo", "photo fooled", "game clone"])

    if is_toy:
        impacto_real = 0.25
        razones.append("Descartado o penalizado: proyecto de juguete o curiosidad sin aplicación corporativa.")
    elif has_enterprise:
        impacto_real = 0.85
        razones.append("Alto impacto ejecutivo: aborda costos, seguridad o procesos operativos en LatAm.")
    else:
        impacto_real = 0.55

    # Veredicto final
    if humo_p >= 0.55 or (n_fuentes == 1 and not has_primary and impacto_real < 0.40):
        veredicto = "descartado"
    elif veracidad_p >= 0.65 and impacto_real >= 0.50 and humo_p <= 0.35:
        veredicto = "valido"
    else:
        veredicto = "dudoso"

    return Verdict(
        narrative_id=narrative.id,
        veracidad_p=veracidad_p,
        impacto_real=impacto_real,
        humo_p=humo_p,
        veredicto=veredicto,
        razones=razones,
        fuentes_verificadas=signals["fuentes"],
        tiene_fuente_primaria=has_primary,
        penalidad_clickbait=round(ratio_cb, 2),
    )


class CriticAgent:
    """Agente auditor de veracidad y filtro anti-humo sin alucinaciones."""

    name: str = "Crítico"

    def run(self, ctx: RunContext) -> AgentResult:
        """Audita cada una de las narrativas identificadas por el Historiador."""
        start_time = time.time()
        logger.info("[%s] Auditando evidencia y veracidad de %d narrativas (run_id=%s)...", self.name, len(ctx.narratives), ctx.run_id)

        verdicts: Dict[str, Verdict] = {}
        verdict_summary = {"valido": 0, "dudoso": 0, "descartado": 0}

        for n in ctx.narratives:
            signals = _evaluate_critic_signals(n)
            verdict = _calibrate_critic_deterministic(signals, n)
            verdicts[n.id] = verdict
            verdict_summary[verdict.veredicto] = verdict_summary.get(verdict.veredicto, 0) + 1

            # Persistir en base de datos
            ctx.db.save_verdict({
                "narrative_id": verdict.narrative_id,
                "veracidad_p": verdict.veracidad_p,
                "impacto_real": verdict.impacto_real,
                "humo_p": verdict.humo_p,
                "veredicto": verdict.veredicto,
                "razones": verdict.razones,
            })

        elapsed_ms = (time.time() - start_time) * 1000
        metrics = {
            "total_auditados": len(verdicts),
            "desglose_veredictos": verdict_summary,
            "tasa_validez": round(verdict_summary["valido"] / max(1, len(verdicts)), 2),
        }

        ctx.db.log_audit(
            run_id=ctx.run_id,
            agente=self.name,
            accion="auditoria_veracidad_completada",
            payload=metrics,
        )

        ctx.verdicts = verdicts

        logger.info(
            "[%s] Finalizado: %d veredictos emitidos (%s) en %.1f ms.",
            self.name,
            len(verdicts),
            verdict_summary,
            elapsed_ms,
        )

        return AgentResult(
            ok=len(verdicts) > 0,
            agent_name=self.name,
            items=list(verdicts.values()),
            metrics=metrics,
            errors=[],
            execution_time_ms=elapsed_ms,
        )
