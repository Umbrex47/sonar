"""Router de Intenciones y Clasificador System One para el Chatbot Radar30X.

Analiza la pregunta del usuario, determina la intención primaria, extrae entidades
y parámetros de filtrado (fase, fuente, tema), y selecciona el nivel de ejecución (T0, T1, T2).
"""

from dataclasses import dataclass, field
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CATALOGO_INTENCIONES_T0 = {
    "temas_en_tendencia",
    "ganchos_usados",
    "que_esta_saturado",
    "novedades_por_fuente",
    "evolucion_de_tema",
    "veredicto_de_tema",
}


@dataclass
class RouterDecision:
    """Decisión tipada emitida por el router de intenciones."""

    intencion: str
    nivel: str  # "T0" | "T1" | "T2"
    confianza: float
    parametros: Dict[str, Any] = field(default_factory=dict)
    requiere_formato: bool = False
    fuera_de_alcance: bool = False
    razon: str = ""


def route_query(pregunta: str, force_level: Optional[str] = None) -> RouterDecision:
    """Clasifica la intención y enruta la pregunta hacia el nivel óptimo.

    Args:
        pregunta: Texto de la pregunta del usuario.
        force_level: Nivel forzado manualmente ("T0", "T1", "T2") para depuración.

    Returns:
        RouterDecision con intención, nivel asignado y parámetros extraídos.
    """
    p_norm = pregunta.lower().strip()
    words = set(re.findall(r"\b\w+\b", p_norm))

    params: Dict[str, Any] = {}

    # Extraer posibles filtros de fase
    if "emergente" in words or "naciendo" in words:
        params["fase"] = "emergente"
    elif "crecimiento" in words or "escalando" in words:
        params["fase"] = "en_crecimiento"
    elif "saturado" in words or "saturada" in words or "refrito" in words or "quemado" in words:
        params["fase"] = "saturado"

    # Extraer posibles filtros de fuente
    for f in ["hackernews", "hacker news", "github", "youtube", "rss", "google"]:
        if f in p_norm:
            params["fuente"] = "HackerNews" if "hacker" in f else f.capitalize()
            break

    # 1. Detección de Fuera de Alcance (Out of Scope)
    patrones_fuera_alcance = [
        r"\b(clima|tiempo en|receta|cocinar|capital de|presidente de|fútbol|partido|chiste|poema|cancion)\b",
        r"\b(quién ganó|cuánto cuesta un vuelo|dólar hoy|tipo de cambio)\b",
    ]
    if any(re.search(pat, p_norm) for pat in patrones_fuera_alcance):
        return RouterDecision(
            intencion="fuera_de_alcance",
            nivel="T0",
            confianza=0.98,
            fuera_de_alcance=True,
            razon="La consulta no está relacionada con tendencias de inteligencia artificial ni con el radar 30X.",
        )

    # 2. Ganchos Usados / Retención
    if any(k in words for k in ["gancho", "ganchos", "hook", "hooks", "retención", "retencion", "psicológico"]):
        # Si pregunta por temas Y ganchos (la pregunta clásica del reto)
        if any(k in words for k in ["tema", "temas", "tendencia", "tendencias", "creciendo"]):
            # Combinación de temas y ganchos -> temas_en_tendencia con detalle de ganchos
            return RouterDecision(
                intencion="temas_en_tendencia",
                nivel=force_level or "T0",
                confianza=0.95,
                parametros=params,
                razon="Pregunta combinada sobre temas en tendencia y ganchos de retención.",
            )
        return RouterDecision(
            intencion="ganchos_usados",
            nivel=force_level or "T0",
            confianza=0.92,
            parametros=params,
            razon="Consulta enfocada en distribución y tipos de ganchos psicológicos.",
        )

    # 3. Qué está saturado / Refritos
    if any(k in words for k in ["saturado", "saturada", "saturados", "refrito", "refritos", "copiado", "copias", "quemado"]):
        return RouterDecision(
            intencion="que_esta_saturado",
            nivel=force_level or "T0",
            confianza=0.94,
            parametros=params,
            razon="Consulta sobre señales saturadas o temas con alto ratio de copias.",
        )

    # 4. Novedades por fuente
    if (params.get("fuente") or any(k in words for k in ["fuente", "fuentes", "origen", "plataforma"])) and any(
        k in words for k in ["nueva", "nuevas", "novedad", "novedades", "salieron", "surgieron", "vistas"]
    ):
        return RouterDecision(
            intencion="novedades_por_fuente",
            nivel=force_level or "T0",
            confianza=0.90,
            parametros=params,
            razon="Consulta sobre distribución de novedades según su fuente de origen.",
        )

    # 5. Evolución de tema / Historial / Trayectoria
    if any(k in words for k in ["evolución", "evolucion", "historia", "trayectoria", "tiempo", "sparkline", "pico", "semanas"]):
        # Extraer posible tema mencionado
        params["tema"] = pregunta
        return RouterDecision(
            intencion="evolucion_de_tema",
            nivel=force_level or "T0",
            confianza=0.88,
            parametros=params,
            razon="Consulta sobre la evolución temporal y serie de menciones de un tema.",
        )

    # 6. Veredicto del Agente Crítico / Veracidad / Humo
    if any(k in words for k in ["veredicto", "veracidad", "humo", "crítico", "critico", "verdad", "fake", "confiable", "auditoría"]):
        params["tema"] = pregunta
        return RouterDecision(
            intencion="veredicto_de_tema",
            nivel=force_level or "T0",
            confianza=0.92,
            parametros=params,
            razon="Consulta de auditoría empírica y filtro anti-humo sobre un tema.",
        )

    # 7. Pregunta Abierta / Estratégica / Exploratoria
    palabras_abiertas = [
        "explica", "explicame", "explícame", "cómo", "como", "compara", "comparar",
        "recomienda", "recomiendame", "recomiéndame", "opinión", "opinion",
        "estrategia", "impacto", "análisis", "analisis", "consejo", "pasos",
        "diferencia", "diferencias", "arquitectura", "profundiza", "detalle",
        "por qué", "porque", "cuál es el", "cual es el", "qué opinas", "que opinas",
        "para qué", "para que", "implementar", "monetizar", "riesgo", "roi",
    ]
    es_pregunta_abierta = any(w in words or w in p_norm for w in palabras_abiertas)

    if force_level in ("T1", "T2") or es_pregunta_abierta:
        return RouterDecision(
            intencion="pregunta_abierta",
            nivel=force_level or "T1",
            confianza=0.92,
            parametros=params,
            razon="Pregunta abierta/exploratoria asignada a modelo ligero T1 con RAG contextual.",
        )

    # 8. Temas en Tendencia / Top (Intención por defecto para preguntas sobre el ranking del radar)
    if any(k in words for k in ["tema", "temas", "tendencia", "tendencias", "creciendo", "top", "radar", "semana"]):
        return RouterDecision(
            intencion="temas_en_tendencia",
            nivel=force_level or "T0",
            confianza=0.95,
            parametros=params,
            razon="Consulta sobre los temas principales y ranking del radar.",
        )

    # 9. Fallback general: Atender como pregunta abierta T1 con modelo ligero
    return RouterDecision(
        intencion="pregunta_abierta",
        nivel=force_level or "T1",
        confianza=0.80,
        parametros={"pregunta_abierta": pregunta},
        razon="Pregunta general no catalogada en T0 canalizada a modelo ligero T1.",
    )


def compute_query_hash(pregunta: str) -> str:
    """Genera un hash SHA-256 normalizado para la caché de respuestas."""
    clean = re.sub(r"\s+", " ", pregunta.lower().strip())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()
