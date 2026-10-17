"""Módulo de redacción narrativa para Radar30X.

Arquitectura Híbrida:
Jev DECIDE (confiable, type-safe, probabilidades calibradas, a escala).
El LLM REDACTA (donde importa la creatividad y el ángulo editorial para 30X).

Genera únicamente los campos 'por_que' y 'adaptacion_30x' para el Top N de temas,
apoyándose en las decisiones ya tomadas por Jev sin reevaluarlas.
"""

import json
import logging
import os
from typing import Dict, Optional, Tuple
import httpx

from pipeline.decide import ClusterDecision
from pipeline.topics import TopicCluster

logger = logging.getLogger(__name__)


def _generate_narrative_template(cluster: TopicCluster, decision: ClusterDecision) -> Tuple[str, str]:
    """Generador narrativo determinista y de alta calidad editorial cuando no hay API de LLM configurada.

    Construye propuestas de adaptación directamente enfocadas en la audiencia de líderes de 30X en LatAm.
    """
    gancho_map = {
        "dato_contraintuitivo": "Dato contraintuitivo que desafía la creencia convencional",
        "contraste": "Comparativa de costos operativos y rendimiento vs métodos tradicionales",
        "tutorial": "Demostración práctica de implementación en menos de 60 segundos",
        "historia": "Caso real de estudio con resultados medibles de productividad",
        "opinion": "Toma de postura estratégica ante el cambio tecnológico",
    }
    gancho_desc = gancho_map.get(decision.gancho, "Ángulo de alto impacto visual y técnico")

    m = cluster.metricas_agregadas
    max_vph = m.get("max_vistas_por_hora", 0.0)
    sources_str = ", ".join(cluster.fuentes)

    if max_vph > 200:
        por_que = f"{gancho_desc}; pico de tracción acelerada ({max_vph:.0f} vistas/h) validado en {sources_str}."
    else:
        por_que = f"{gancho_desc}; discusión emergente con validación cruzada en {sources_str}."

    # Propuestas editoriales de adaptación para 30X según el formato y el tema
    tema_clean = cluster.tema_canonico.replace("Herramienta: ", "")
    formato_sug = decision.formato

    if formato_sug == "video_corto":
        adaptacion = (
            f"Video corto/Reel: '3 errores comunes al implementar {tema_clean} en tu empresa' "
            f"+ carrusel de síntesis ejecutiva en LinkedIn."
        )
    elif formato_sug == "carousel":
        adaptacion = (
            f"Carrusel LinkedIn: 'Guía ejecutiva para directivos: Cómo evaluar {tema_clean} "
            f"sin gastar una fortuna' + infografía de arquitectura."
        )
    elif formato_sug == "hilo":
        adaptacion = (
            f"Hilo de análisis técnico-estratégico: 'Desglosamos la arquitectura detrás de {tema_clean} "
            f"y cómo afecta a los equipos en Latinoamérica'."
        )
    elif formato_sug == "articulo":
        adaptacion = (
            f"Artículo de fondo: 'El impacto real de {tema_clean} en la competitividad regional: "
            f"lo que los directores de innovación deben saber este trimestre'."
        )
    else:
        adaptacion = (
            f"Masterclass / Video largo: 'Implementación práctica de {tema_clean}: "
            f"de la teoría a la producción en 30 minutos'."
        )

    return por_que, adaptacion


def _call_openai_compatible(
    cluster: TopicCluster,
    decision: ClusterDecision,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> Optional[Tuple[str, str]]:
    """Llama a un endpoint compatible con OpenAI para redactar el por qué y la adaptación."""
    prompt = f"""Eres el editor senior de 30X, medio líder de educación en Inteligencia Artificial para directivos y equipos en Latinoamérica.
Jev (TypeSafe System One) ya ha tomado de forma definitiva las siguientes decisiones estructuradas sobre una tendencia:

Tema: {cluster.tema_canonico}
Fase: {decision.fase}
Gancho narrativo: {decision.gancho}
Formato óptimo: {decision.formato}
Nivel de encaje con líderes LatAm: {decision.encaje_audiencia:.2f}
Métricas y señales: {cluster.metricas_agregadas}

NO cambies las decisiones de Jev. Redacta únicamente dos campos en JSON:
- "por_que": Explicación concisa (1 oración) de por qué este contenido está funcionando en redes.
- "adaptacion_30x": Recomendación concreta de adaptación editorial para 30X (especificando formato sugerido y titular de gancho).

Responde exclusivamente con un JSON válido con estas dos claves.
"""
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return parsed.get("por_que", ""), parsed.get("adaptacion_30x", "")
    except Exception as exc:
        logger.warning("Fallo al llamar LLM de redacción: %s", exc)
    return None


def generate_narrative(cluster: TopicCluster, decision: ClusterDecision) -> Tuple[str, str]:
    """Genera la narrativa editorial ('por_que' y 'adaptacion_30x') para un tema destacado.

    Utiliza el LLM configurado (OpenAI, DeepSeek, etc.) o el motor editorial de plantilla determinista.
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if api_key and provider in ("openai", "deepseek", "groq"):
        base_urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "groq": "https://api.groq.com/openai/v1",
        }
        base_url = base_urls.get(provider, "https://api.openai.com/v1")
        res = _call_openai_compatible(cluster, decision, api_key, base_url, model)
        if res:
            return res

    # Fallback editorial determinista de alta calidad
    return _generate_narrative_template(cluster, decision)
