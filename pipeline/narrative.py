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


def _generate_audience_fit_reason(cluster: TopicCluster, decision: ClusterDecision) -> str:
    """Explica con precisión por qué la tendencia coincide con el perfil y las prioridades de la audiencia 30X.

    Audiencia objetivo: CEOs, fundadores, directores de tecnología (CTO), operaciones (COO)
    e innovación en empresas de Latinoamérica, enfocados en ROI, costos y ventaja competitiva.
    """
    tema_lower = cluster.tema_canonico.lower()

    if "polémica" in tema_lower or "polemica" in tema_lower or "anthropic" in tema_lower or "openai" in tema_lower:
        return (
            "Alerta de riesgo de continuidad operativa para directores y comités de riesgo: "
            "depender de una única API propietaria expone a cambios repentinos de términos, "
            "precios o disputas de propiedad intelectual que paralizan productos en producción."
        )
    elif "benchmark" in tema_lower or "razonamiento" in tema_lower or "slm" in tema_lower:
        return (
            "Impacto financiero directo para directores de tecnología y finanzas (CTO/CFO): "
            "demuestra cómo reemplazar modelos ultra-costosos por modelos abiertos o destilados "
            "reduce la factura de nube entre un 70% y un 85% sin sacrificar precisión."
        )
    elif "coding" in tema_lower or "desarrollo" in tema_lower:
        return (
            "Resuelve la escasez y alto costo de talento técnico senior en LatAm: "
            "permite a squads pequeños multiplicar x3 su velocidad de entrega de producto digital "
            "utilizando agentes de desarrollo autónomo supervisados."
        )
    elif "rpa" in tema_lower or "operaciones" in tema_lower:
        return (
            "Prioridad crítica para directores de operaciones (COO): las empresas en la región "
            "arrastran automatizaciones frágiles en RPA legado; los agentes autónomos reducen "
            "el mantenimiento a una fracción y gestionan excepciones complejas de negocio."
        )
    elif "sandbox" in tema_lower or "seguridad" in tema_lower or "ciberseguridad" in tema_lower:
        return (
            "Tranquilidad y gobernanza para CISOs y directores de compliance: "
            "establece las pautas para desplegar agentes con permisos de ejecución "
            "sin riesgo de fuga de datos sensibles corporativos ni inyecciones maliciosas."
        )
    elif "ceo" in tema_lower or "liderazgo" in tema_lower:
        return (
            "Desarrollo de liderazgo para directores generales y founders: "
            "ofrece marcos accionables para delegar análisis estratégico y toma de decisiones "
            "en agentes inteligentes liberando más de 15 horas de trabajo gerencial reactivo por semana."
        )
    elif "oportunidades" in tema_lower or "roi" in tema_lower:
        return (
            "Alineación total con comités de dirección y CFOs: elimina experimentos de IA abstractos "
            "y se enfoca en proyectos corporativos con retorno medible de inversión en menos de 90 días."
        )
    elif "compliance" in tema_lower or "auditoría" in tema_lower or "adopción" in tema_lower or "laboral" in tema_lower:
        return (
            "De alta relevancia para directores de talento y asuntos legales: "
            "brinda claridad sobre regulación laboral emergente, reconversión de perfiles y "
            "preparación para auditorías formales de uso de IA en la región."
        )
    elif "memoria" in tema_lower or "contexto" in tema_lower:
        return (
            "Optimización para líderes de producto y servicio al cliente: "
            "permite crear asistentes empresariales que retienen el contexto histórico de clientes "
            "sin saturar la ventana de contexto ni inflar los costos de inferencia."
        )
    else:
        afinidad_pct = int(round(decision.encaje_audiencia * 100))
        return (
            f"Alta afinidad ({afinidad_pct}%) con líderes de negocio en LatAm: "
            f"aborda reducción de costos operativos, mitigación de riesgos tecnológicos "
            f"y adopción práctica de IA con foco en productividad medible."
        )


def _generate_narrative_template(cluster: TopicCluster, decision: ClusterDecision) -> Tuple[str, str, str]:
    """Generador narrativo determinista y de alta calidad editorial cuando no hay API de LLM configurada.

    Construye por_que, por_que_audiencia y adaptacion_30x directamente enfocadas en líderes en LatAm.
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

    por_que_audiencia = _generate_audience_fit_reason(cluster, decision)

    # Propuestas editoriales de adaptación para 30X con ángulos punchy de alto impacto
    tema_lower = cluster.tema_canonico.lower()
    tema_clean = cluster.tema_canonico.replace("-", " ").replace("/", " / ").title()

    if "rpa" in tema_lower or "operaciones" in tema_lower:
        adaptacion = (
            "Short / Reel: 'Por qué tu empresa debe matar el RPA antes de 2027: Agentes autónomos explicados en 60s' "
            "+ checklist de migración operativa en LinkedIn."
        )
    elif "sandbox" in tema_lower or "seguridad" in tema_lower:
        adaptacion = (
            "Carrusel LinkedIn: 'Alerta de Ciberseguridad: 3 capas para evitar que tus agentes de IA ejecuten comandos no autorizados en producción' "
            "+ infografía de arquitectura de aislamiento."
        )
    elif "coding" in tema_lower or "desarrollo" in tema_lower:
        adaptacion = (
            "Hilo en X / LinkedIn: 'El fin del autocompletado de código: Cómo los agentes en Slack y Linear están triplicando la velocidad de los equipos de producto en LatAm'."
        )
    elif "razonamiento" in tema_lower or "slm" in tema_lower:
        adaptacion = (
            "Masterclass / Video de fondo: 'Cómo correr modelos de razonamiento open-source en servidores locales y reducir un 80% tu factura de APIs en la nube'."
        )
    elif "adopción" in tema_lower or "laboral" in tema_lower or "empleo" in tema_lower:
        adaptacion = (
            "Artículo de fondo & Newsletter: 'El 90% de las empresas en LatAm formalizan IA: Qué puestos de trabajo se están creando y cuáles desaparecen este trimestre'."
        )
    elif "compliance" in tema_lower or "auditoría" in tema_lower or "gobernanza" in tema_lower:
        adaptacion = (
            "Carrusel infográfico: 'Alerta legal para directores de talento: 4 requisitos de auditoría de IA que entran en vigor este año en la región'."
        )
    elif "polémica" in tema_lower or "polemica" in tema_lower or "anthropic" in tema_lower or "openai" in tema_lower:
        adaptacion = (
            "Hilo de análisis & Video: 'Guerra Fría en IA: Qué revela la disputa de seguridad y la ruptura de alianzas sobre el riesgo de tu proveedor de APIs'."
        )
    elif "benchmark" in tema_lower:
        adaptacion = (
            "Guía ejecutiva: 'Corte de caja de Benchmarks: ¿Realmente necesitas pagar modelos premium o uno abierto cubre el 95% de tus casos de negocio?'"
        )
    elif "ceo" in tema_lower or "liderazgo" in tema_lower:
        adaptacion = (
            "Columna de Liderazgo & Newsletter: 'El CEO aumentado: 5 rutinas para delegar análisis estratégico en agentes sin perder la brújula del negocio'."
        )
    elif "oportunidades" in tema_lower or "roi" in tema_lower:
        adaptacion = (
            "Reporte exclusivo 30X: 'Calculadora de ROI: 3 proyectos de IA corporativa que pagan su inversión en menos de 90 días'."
        )
    elif "memoria" in tema_lower:
        adaptacion = (
            "Video corto / Reel: 'El truco de la memoria persistente local: Cómo evitar que tus agentes corporativos olviden el contexto entre sesiones'."
        )
    elif decision.formato == "video_corto":
        adaptacion = (
            f"Video corto / Reel: '3 errores comunes al implementar {tema_clean} en tu empresa' "
            f"+ carrusel de síntesis ejecutiva en LinkedIn."
        )
    elif decision.formato == "carousel":
        adaptacion = (
            f"Carrusel LinkedIn: 'Guía ejecutiva: Cómo evaluar {tema_clean} "
            f"sin gastar una fortuna' + infografía de decisión."
        )
    else:
        adaptacion = (
            f"Artículo de fondo / Newsletter: 'El impacto real de {tema_clean} en la competitividad corporativa: "
            f"lo que los directores de innovación deben saber'."
        )

    return por_que, por_que_audiencia, adaptacion


def _call_openai_compatible(
    cluster: TopicCluster,
    decision: ClusterDecision,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> Optional[Tuple[str, str, str]]:
    """Llama a un endpoint compatible con OpenAI para redactar el por qué, el encaje de audiencia y la adaptación."""
    prompt = f"""Eres el editor senior de 30X, medio líder de educación en Inteligencia Artificial para directivos y equipos en Latinoamérica.
Jev (TypeSafe System One) ya ha tomado de forma definitiva las siguientes decisiones estructuradas sobre una tendencia:

Tema: {cluster.tema_canonico}
Fase: {decision.fase}
Gancho narrativo: {decision.gancho}
Formato óptimo: {decision.formato}
Nivel de encaje con líderes LatAm: {decision.encaje_audiencia:.2f}
Métricas y señales: {cluster.metricas_agregadas}

NO cambies las decisiones de Jev. Redacta únicamente tres campos en JSON:
- "por_que": Explicación concisa (1 oración) de por qué este contenido está funcionando en redes/medios.
- "por_que_audiencia": Explicación clara (1-2 oraciones) de por qué esta tendencia coincide directamente con el perfil y prioridades de la audiencia de líderes, CEOs y directores de tecnología/operaciones en Latinoamérica (ahorro de costos, mitigación de riesgos de API, productividad o ROI en < 90 días).
- "adaptacion_30x": Recomendación concreta de adaptación editorial para 30X (especificando formato sugerido y titular de gancho).

Responde exclusivamente con un JSON válido con estas tres claves.
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
                return (
                    parsed.get("por_que", ""),
                    parsed.get("por_que_audiencia", _generate_audience_fit_reason(cluster, decision)),
                    parsed.get("adaptacion_30x", ""),
                )
    except Exception as exc:
        logger.warning("Fallo al llamar LLM de redacción: %s", exc)
    return None


def generate_narrative(cluster: TopicCluster, decision: ClusterDecision) -> Tuple[str, str, str]:
    """Genera la narrativa editorial ('por_que', 'por_que_audiencia' y 'adaptacion_30x') para un tema destacado.

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
