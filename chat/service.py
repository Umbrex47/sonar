"""Servicio orquestador del Chatbot RAG para Radar30X.

Gestiona el ciclo de vida de cada consulta:
1. Verificación en caché de respuestas.
2. Enrutamiento de intención con Jev / Router.
3. Ejecución en el nivel correspondiente (T0 determinista en F1).
4. Persistencia en caché y observabilidad en chat_logs.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import os
from chat.router import compute_query_hash, route_query
from chat.t0_deterministic import execute_t0_query
from pipeline.db import Database

logger = logging.getLogger(__name__)


class ChatService:
    """Servicio principal de atención de consultas RAG."""

    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or Database()

    def ask(
        self,
        pregunta: str,
        no_cache: bool = False,
        force_level: Optional[str] = None,
        show_sources: bool = False,
    ) -> Dict[str, Any]:
        """Procesa una consulta del usuario y retorna la respuesta estructurada."""
        start_time = time.time()
        query_hash = compute_query_hash(pregunta)

        # 1. Comprobar caché si no está deshabilitada
        if not no_cache:
            cached = self.db.get_cached_answer(query_hash)
            if cached and isinstance(cached.get("respuesta"), dict):
                resp = cached["respuesta"]
                resp["desde_cache"] = True
                return resp

        # 2. Enrutar intención
        decision = route_query(pregunta, force_level=force_level)

        # 3. Caso fuera de alcance
        if decision.fuera_de_alcance:
            res = {
                "respuesta": (
                    "🤖 **Radar 30X // Fuera de Alcance:**\n\n"
                    "Esta plataforma está especializada exclusivamente en **tendencias, señales emergentes, "
                    "fases evolutivas y ganchos de contenido sobre Inteligencia Artificial** para líderes y equipos en Latinoamérica.\n\n"
                    f"Su consulta ('*{pregunta}*') no corresponde al ámbito del radar. "
                    "Pruebe con preguntas como:\n"
                    "- *'¿Cuáles son los temas en tendencia y qué ganchos están usando?'*\n"
                    "- *'¿Qué temas de IA están saturados esta semana?'*\n"
                    "- *'¿Qué novedades emergentes salieron en HackerNews?'*"
                ),
                "nivel": "T0",
                "intencion": "fuera_de_alcance",
                "fuentes": [],
                "confianza": 0.99,
                "escalado": False,
                "razon_escalado": None,
                "latencia_ms": round((time.time() - start_time) * 1000, 1),
            }
            return res

        # 4. Ejecución: Si se clasifica o fuerza como T0, usar determinista instantáneo (<50ms, $0 marginal).
        # Si es pregunta abierta o nivel T1/T2 (o se fuerza T1/T2), invocar el sintetizador RAG / modelo abierto.
        if force_level == "T0" or (decision.nivel == "T0" and force_level not in ("T1", "T2")):
            result = execute_t0_query(
                intencion=decision.intencion,
                pregunta=pregunta,
                db=self.db,
                params=decision.parametros,
            )
        elif decision.intencion == "pregunta_abierta" or decision.nivel in ("T1", "T2") or force_level in ("T1", "T2"):
            from chat.open_model import answer_open_question
            ground_truth = None
            if decision.intencion != "pregunta_abierta":
                try:
                    ground_truth = execute_t0_query(
                        intencion=decision.intencion,
                        pregunta=pregunta,
                        db=self.db,
                        params=decision.parametros,
                    )
                except Exception as ex:
                    logger.warning("Error al calcular ground truth T0: %s", ex)

            result = answer_open_question(
                pregunta=pregunta,
                db=self.db,
                force_level=force_level or decision.nivel or "T1",
                show_sources=show_sources,
                ground_truth=ground_truth,
            )
            if decision.intencion != "pregunta_abierta":
                result["intencion"] = decision.intencion
        else:
            result = execute_t0_query(
                intencion=decision.intencion,
                pregunta=pregunta,
                db=self.db,
                params=decision.parametros,
            )

        # 5. Guardar en caché si la confianza es alta
        if result.get("confianza", 0) >= 0.80 and not no_cache:
            try:
                self.db.cache_answer(
                    query_hash=query_hash,
                    pregunta=pregunta,
                    respuesta_data=result,
                    nivel=result.get("nivel", decision.nivel),
                )
            except Exception as e:
                logger.warning("Error al guardar en answers_cache: %s", e)

        # 6. Observabilidad: Registrar en chat_logs
        try:
            self.db.save_chat_log({
                "query_hash": query_hash,
                "pregunta": pregunta,
                "intencion": result.get("intencion", decision.intencion),
                "nivel": result.get("nivel", decision.nivel),
                "latencia_ms": result.get("latencia_ms", round((time.time() - start_time) * 1000, 1)),
                "confianza": result.get("confianza", decision.confianza),
            })
        except Exception as e:
            logger.debug("Error al guardar en chat_logs: %s", e)

        return result
