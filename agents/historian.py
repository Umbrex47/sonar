"""Agente Historiador (HistorianAgent) para Radar30X.

Responsabilidad: Comparar cada cluster de noticias contra la memoria histórica de 90 días,
calcular novedad probabilística, recurrencia, fechas de pico y ratio de copias,
para clasificar con rigor la fase evolutiva (Emergente, Crecimiento, Saturado, Resurgente).
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agents.base import AgentResult, Narrative, RunContext
from pipeline.knowledge.vector_store import VectorStore
from pipeline.topics import TopicCluster, cluster_items
from sources.base import RawItem

logger = logging.getLogger(__name__)


def cosine_sim(v1: List[float], v2: List[float]) -> float:
    """Calcula similitud coseno entre dos vectores numéricos."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def generate_sparkline(counts: List[int]) -> str:
    """Genera una representación ASCII compacta de la serie temporal (ej. .:oO*)."""
    if not counts or max(counts) == 0:
        return "......"
    max_c = max(counts)
    symbols = [".", ":", "o", "O", "*"]
    out = []
    # Usar las últimas 6 a 8 semanas para alta visibilidad
    window = counts[-8:] if len(counts) >= 8 else counts
    for c in window:
        if c == 0:
            out.append(".")
        else:
            idx = min(int((c / max_c) * (len(symbols) - 1)), len(symbols) - 1)
            out.append(symbols[idx])
    return "".join(out)


class HistorianAgent:
    """Agente guardián de la memoria narrativa y clasificador temporal."""

    name: str = "Historiador"

    def __init__(self, vector_store: Optional[VectorStore] = None) -> None:
        self.vector_store = vector_store or VectorStore()

    def run(self, ctx: RunContext) -> AgentResult:
        """Compara los clusters actuales con la memoria histórica de 90 días."""
        start_time = time.time()
        logger.info("[%s] Consultando memoria histórica de 90 días (run_id=%s)...", self.name, ctx.run_id)

        # 1. Agrupar ítems actuales en clusters si aún no se han agrupado
        clusters: List[TopicCluster] = ctx.clusters
        if not clusters:
            if not ctx.items:
                ctx.items = ctx.db.get_all_items()
            clusters = cluster_items(ctx.items, similarity_threshold=75.0)
            ctx.clusters = clusters

        # 2. Recuperar historial de 90 días de la base de datos
        history_items = ctx.db.get_items_history(days=90)
        logger.info("[%s] Memoria contiene %d ítems históricos en ventana de 90 días.", self.name, len(history_items))

        # Precargar vectores históricos
        history_vectors: List[Tuple[Dict[str, Any], List[float]]] = []
        for h_item in history_items[:400]:  # Límite eficiente para evaluación
            text = f"{h_item['titulo']} | {h_item['resumen']}"
            vec = self.vector_store.generate_embedding(text)
            history_vectors.append((h_item, vec))

        narratives: List[Narrative] = []
        now_dt = datetime.now(timezone.utc)

        for cl in clusters:
            cluster_text = f"{cl.tema_canonico} | {' '.join(cl.titulos_muestra(3))}"
            cluster_vec = self.vector_store.generate_embedding(cluster_text)
            cl_items_ids = {it.id for it in cl.items}

            # Buscar similitudes contra el historial
            matches: List[Tuple[Dict[str, Any], float]] = []
            max_similarity = 0.0

            for h_item, h_vec in history_vectors:
                # Evitar comparar un ítem contra sí mismo si fue recién insertado
                if h_item["id"] in cl_items_ids:
                    continue
                sim = cosine_sim(cluster_vec, h_vec)
                if sim > max_similarity:
                    max_similarity = sim
                if sim >= 0.70:
                    matches.append((h_item, sim))

            # Novedad: Si no hay match histórico, es 1.0 (absolutamente nuevo)
            novelty = round(max(0.0, min(1.0, 1.0 - max_similarity)), 3)

            # Bucketización semanal (12 semanas = ~90 días)
            weekly_mentions = [0] * 12
            weeks_with_match = set()

            for h_item, sim in matches:
                item_date_str = h_item.get("fecha")
                try:
                    if item_date_str:
                        # Limpiar timezone format si es necesario
                        clean_date = item_date_str.replace("Z", "+00:00")
                        item_dt = datetime.fromisoformat(clean_date)
                        if item_dt.tzinfo is None:
                            item_dt = item_dt.replace(tzinfo=timezone.utc)
                    else:
                        item_dt = now_dt
                except Exception:
                    item_dt = now_dt

                age_days = max(0, (now_dt - item_dt).days)
                week_idx = 11 - min(11, age_days // 7)
                weekly_mentions[week_idx] += 1
                weeks_with_match.add(week_idx)

            # Sumar las menciones del cluster actual a la semana más reciente (semana 11)
            weekly_mentions[11] += len(cl.items)
            weeks_with_match.add(11)

            # Recurrencia: Número de semanas distintas con actividad
            recurrencia = len(weeks_with_match)

            # Pico histórico
            peak_week_idx = int(np.argmax(weekly_mentions))
            peak_mentions = weekly_mentions[peak_week_idx]
            semanas_desde_pico = 11 - peak_week_idx
            peak_date = (now_dt - timedelta(days=semanas_desde_pico * 7)).strftime("%Y-%m-%d")

            # Ratio de copias en ventana de 48h (piezas casi idénticas entre sí en el cluster)
            cluster_items_list = cl.items
            copy_pairs = 0
            total_pairs = 0
            for i in range(len(cluster_items_list)):
                for j in range(i + 1, len(cluster_items_list)):
                    total_pairs += 1
                    t1 = cluster_items_list[i].titulo.lower()
                    t2 = cluster_items_list[j].titulo.lower()
                    from rapidfuzz import fuzz
                    if fuzz.token_set_ratio(t1, t2) >= 88:
                        copy_pairs += 1

            ratio_copias = round(copy_pairs / total_pairs, 2) if total_pairs > 0 else 0.0

            # Creadores / fuentes distintas
            fuentes_distintas = len(cl.fuentes)

            # Clasificación de Fase (Taxonomía formal del plan)
            if novelty >= 0.25 and semanas_desde_pico <= 1 and fuentes_distintas >= 2:
                fase = "emergente"  # Señal Temprana
            elif semanas_desde_pico >= 3 and ratio_copias >= 0.40:
                fase = "saturado"  # Todos lo copiaron hace semanas
            elif semanas_desde_pico >= 4 and weekly_mentions[11] > weekly_mentions[10] and weekly_mentions[10] <= weekly_mentions[peak_week_idx] * 0.4:
                fase = "resurgente"  # Decaimiento previo y nuevo despegue
            elif weekly_mentions[11] >= weekly_mentions[10] and peak_week_idx >= 10:
                fase = "crecimiento"  # Subiendo con volumen activo
            else:
                fase = "crecimiento" if novelty >= 0.20 else "saturado"

            sparkline = generate_sparkline(weekly_mentions)
            first_seen = (now_dt - timedelta(days=(11 - min(weeks_with_match)) * 7)).strftime("%Y-%m-%d") if weeks_with_match else now_dt.strftime("%Y-%m-%d")

            narrative = Narrative(
                id=cl.cluster_id,
                tema=cl.tema_canonico,
                items=cl.items,
                first_seen=first_seen,
                last_seen=now_dt.strftime("%Y-%m-%d"),
                fase=fase,
                novelty=novelty,
                recurrencia=recurrencia,
                pico_fecha=peak_date,
                semanas_desde_pico=semanas_desde_pico,
                ratio_copias=ratio_copias,
                fuentes_distintas=fuentes_distintas,
                sparkline=sparkline,
                menciones_historicas=weekly_mentions,
                score_historico=round(float(len(cl.items)), 3),
            )
            narratives.append(narrative)

            # Persistir en SQLite
            ctx.db.save_narrative(
                narrative_data={
                    "id": narrative.id,
                    "nombre": narrative.tema,
                    "first_seen": narrative.first_seen,
                    "last_seen": narrative.last_seen,
                    "fase": narrative.fase,
                    "novelty": narrative.novelty,
                    "recurrencia": narrative.recurrencia,
                    "pico_fecha": narrative.pico_fecha,
                    "semanas_desde_pico": narrative.semanas_desde_pico,
                    "ratio_copias": narrative.ratio_copias,
                    "fuentes_distintas": narrative.fuentes_distintas,
                    "sparkline": narrative.sparkline,
                },
                items=[{"item_id": it.id, "similitud": 1.0} for it in cl.items],
            )

        elapsed_ms = (time.time() - start_time) * 1000
        fases_summary = {}
        for n in narratives:
            fases_summary[n.fase] = fases_summary.get(n.fase, 0) + 1

        metrics = {
            "total_narrativas_evaluadas": len(narratives),
            "desglose_fases": fases_summary,
            "items_historicos_comparados": len(history_items),
        }

        ctx.db.log_audit(
            run_id=ctx.run_id,
            agente=self.name,
            accion="evaluacion_historica_completada",
            payload=metrics,
        )

        ctx.narratives = narratives

        logger.info(
            "[%s] Finalizado: %d narrativas analizadas. Fases: %s (%.1f ms).",
            self.name,
            len(narratives),
            fases_summary,
            elapsed_ms,
        )

        return AgentResult(
            ok=len(narratives) > 0,
            agent_name=self.name,
            items=narratives,
            metrics=metrics,
            errors=[],
            execution_time_ms=elapsed_ms,
        )
