"""Módulo generador de borradores editoriales con LLM para Radar30X.

Transforma tendencias, narrativas y decisiones de Jev en piezas editoriales completas
(video corto/reels, carruseles, hilos y artículos) adaptadas para directivos y líderes
en Latinoamérica (30X Media).
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger(__name__)


def _generate_draft_deterministic(
    titulo: str,
    formato: str,
    gancho: str,
    evidencia: List[str],
    narrative_context: Optional[Dict[str, Any]] = None,
    autor: str = "30X Media",
) -> str:
    """Generador determinista de alta fidelidad cuando no hay conexión a LLM."""
    narrative_context = narrative_context or {}
    por_que = narrative_context.get(
        "por_que",
        "Alta tracción en comunidades tecnológicas y repositorios open source en los últimos 7 días."
    )
    por_que_audiencia = narrative_context.get(
        "por_que_audiencia",
        "Responde a la necesidad de optimización de costos de infraestructura y mitigación de dependencia en APIs propietarias para empresas en LatAm."
    )
    adaptacion_30x = narrative_context.get(
        "adaptacion_30x",
        f"Presentar un marco de acción concreto comparando alternativas y cuantificando el impacto en ROI."
    )
    fase = narrative_context.get("fase", "Crecimiento")

    gancho_clean = gancho.replace("_", " ").capitalize()

    # Formatos específicos
    if formato == "video_corto":
        estructura_guion = f"""### ⏱️ Estructura y Escaleta (60 Segundos)
- **0:00 - 0:05 | Hook Verbal y Visual:**
  *(En cámara, mirando fijamente, gráfico en pantalla)*
  "Si tu empresa todavía paga miles de dólares en APIs propietarias por esta función de IA, estás perdiendo el 80% de tu margen sin darte cuenta."
- **0:05 - 0:18 | Planteamiento del Problema / Fricción:**
  "La mayoría de directores en la región creen que necesitan los modelos más grandes y caros. Pero el verdadero cuello de botella es la latencia y el bloqueo de proveedor."
- **0:18 - 0:42 | El Quiebre / Demostración:**
  "{por_que} Con esta arquitectura o modelo abierto, equipos pequeños están logrando la misma precisión con una fracción del cómputo."
- **0:42 - 0:55 | Implicación Estratégica para Líderes:**
  "{por_que_audiencia}"
- **0:55 - 1:00 | Llamado a la Acción (CTA):**
  "¿Ya lo probaste en tu equipo técnico? Comenta 'RADAR' y te compartimos el enlace con los benchmarks verificados."
"""
    elif formato == "carrusel":
        estructura_guion = f"""### 📑 Estructura Slide por Slide (LinkedIn / Instagram)
- **Slide 1 (Portada Magnética):**
  - Titular: "{titulo}"
  - Subtítulo: "Por qué los directivos que ignoran esta señal pagarán el doble en su infraestructura de IA."
- **Slide 2 (El Contexto):**
  - "El mercado acaba de cambiar. Lo que antes requería infraestructura de millones de dólares, hoy corre en entornos controlados y destilados."
- **Slide 3 (El Problema Oculto):**
  - "El error común: asumir que más parámetros equivalen a mejor retorno de inversión en producción."
- **Slide 4 (Los Datos Empíricos):**
  - "{por_que}"
- **Slide 5 (Estrategia para Empresas en LatAm):**
  - "{por_que_audiencia}"
- **Slide 6 (Hoja de Ruta de Implementación):**
  - "1. Auditar casos de uso actuales. 2. Desplegar pruebas de concepto con sandboxing. 3. Medir reducción de latencia y costo por token."
- **Slide 7 (Conclusión & CTA):**
  - "Guarda este post para tu próxima reunión de tecnología con tu CTO o equipo de innovación."
"""
    elif formato == "hilo":
        estructura_guion = f"""### 🧵 Hilo Editorial (X / Twitter / LinkedIn Pulse)
**1/6 (Hook Tweet):**
{titulo}. Pocos directivos lo están viendo venir, pero el impacto en costos de nube y operaciones será monumental. Aquí el análisis estratégico 👇

**2/6 (Contexto):**
Durante meses, la narrativa dominante fue depender ciegamente de soluciones cerradas. Pero los datos recientes demuestran un punto de inflexión.

**3/6 (El Hecho Concreto):**
{por_que}

**4/6 (El Impacto en LatAm):**
{por_que_audiencia}

**5/6 (Adaptación 30X):**
{adaptacion_30x}

**6/6 (Cierre & CTA):**
¿Qué opinas? ¿Tu empresa ya evalúa modelos locales o sigues dependiendo de una sola API? Síguenos en @30XMedia para más inteligencia semanal.
"""
    else:  # articulo
        estructura_guion = f"""### 📰 Artículo Ejecutivo / Newsletter
#### Entradilla Ejecutiva
{titulo} representa uno de los movimientos tectónicos más relevantes de esta semana en el ecosistema de inteligencia artificial. Lejos del ruido mediático, este avance plantea preguntas de fondo sobre viabilidad económica y soberanía tecnológica en empresas de América Latina.

#### El Punto de Inflexión Tecnológico
{por_que}

#### Análisis de Viabilidad y Retorno de Inversión (ROI)
{por_que_audiencia}

#### Recomendaciones para Comités de Dirección y Equipos de Tecnología
{adaptacion_30x}
"""

    body = f"""# {titulo}

## 🎯 Ganchos de Apertura (Hook Options)
1. **{gancho_clean}:** "El 90% de los líderes creen que la IA avanzada requiere presupuestos millonarios. Esta prueba demuestra lo contrario."
2. **Pregunta Provocadora:** "¿Cuánto dinero está quemando tu empresa cada mes por no actualizar la arquitectura de tus agentes de IA?"
3. **Contraste de Mercado:** "Mientras los grandes labs compiten por titulares, las startups ágiles están capturando márgenes reduciendo costos un 75%."

## 📝 Guion y Estructura Editorial ({formato.replace('_', ' ').title()})
{estructura_guion}

## 💼 Ángulo Ejecutivo 30X (Audiencia LatAm)
- **Fase de Adopción:** {fase}
- **Impacto Financiero:** {por_que_audiencia}
- **Recomendación 30X:** {adaptacion_30x}

## 🔍 Evidencia y Fuentes de Respaldo
"""
    for u in evidencia:
        body += f"- {u}\n"
    if not evidencia:
        body += "- *Fuentes verificadas en memoria vectorial de Radar30X*\n"

    body += """
## 📋 Notas de Producción
- **Tono:** Directo, sobrio, sin hype vacío ni jerga innecesaria.
- **Recursos visuales recomendados:** Gráfico de comparativa de costos, esquema de arquitectura de agentes o captura de benchmark oficial.
- **Hashtags sugeridos:** #InteligenciaArtificial #TechLeadership #ROI #StartupsLatAm #Radar30X
"""
    return body


def _generate_with_gemini(
    prompt: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
) -> Optional[str]:
    """Llama a Google Gemini para generar el borrador editorial."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    try:
        with httpx.Client(timeout=30.0, trust_env=False) as client:
            resp = client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.35,
                        "maxOutputTokens": 8192,
                    },
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [])
                if cand:
                    text = cand[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if text:
                        return text.strip()
            else:
                logger.warning("Gemini devolvió código HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Fallo al llamar Gemini para borrador: %s", exc)
    return None


def _generate_with_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> Optional[str]:
    """Llama a un endpoint compatible con OpenAI (OpenAI, DeepSeek, Groq)."""
    try:
        with httpx.Client(timeout=30.0, trust_env=False) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Eres el Director Editorial y Guionista Senior de 30X, la plataforma líder de educación "
                                "e inteligencia estratégica en Inteligencia Artificial para CEOs, directivos de tecnología (CTO/CIO) "
                                "y líderes de operaciones en Latinoamérica. Redacta en Markdown pulido, pragmático y de alto impacto."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.35,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content:
                    return content.strip()
    except Exception as exc:
        logger.warning("Fallo al llamar OpenAI compatible para borrador: %s", exc)
    return None


def generate_draft_body_llm(
    titulo: str,
    formato: str = "video_corto",
    gancho: str = "opinion",
    evidencia: Optional[List[str]] = None,
    narrative_context: Optional[Dict[str, Any]] = None,
    autor: str = "30X Media",
) -> str:
    """Genera el contenido Markdown de un borrador editorial utilizando LLM con fallback robusto."""
    evidencia = evidencia or []
    narrative_context = narrative_context or {}

    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    api_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    por_que = narrative_context.get("por_que", "Alta tracción y validación empírica en la última semana.")
    por_que_audiencia = narrative_context.get(
        "por_que_audiencia",
        "Afinidad con reducción de costos de inferencia, mitigación de riesgo de vendor lock-in y productividad directiva en LatAm."
    )
    adaptacion_30x = narrative_context.get(
        "adaptacion_30x",
        "Presentar comparativa táctica con foco en ROI medible a 90 días."
    )
    fase = narrative_context.get("fase", "Crecimiento")

    prompt = f"""Eres el Director Editorial y Guionista Senior de 30X Media.
Debes redactar un BORRADOR EDITORIAL COMPLETO Y LISTO PARA PRODUCCIÓN sobre la siguiente tendencia de Inteligencia Artificial:

TÍTULO DEL TEMA: {titulo}
FORMATO OBJETIVO: {formato} (ej: video_corto / carrusel / hilo / articulo)
TÉCNICA DE GANCHO PSICOLÓGICO: {gancho}
FASE DE ADOPCIÓN DETECTADA: {fase}
POR QUÉ ES TENDENCIA: {por_que}
ENCAJE CON DIRECTIVOS LATAM (30X): {por_que_audiencia}
ADAPTACIÓN EDITORIAL SUGERIDA: {adaptacion_30x}
FUENTES Y ENLACES DE EVIDENCIA:
{chr(10).join(f"- {e}" for e in evidencia) if evidencia else "- Sin enlaces específicos"}

INSTRUCCIONES EDITORIALES ESTRICTAS:
1. No uses marcadores de posición genéricos como '[Gancho aquí]' o '[Desarrollo]'. REDACTA cada palabra del guion o contenido.
2. Tono: Ejecutivo, analítico, contundente, cero humo, enfocado en ROI, toma de decisiones y ventajas competitivas reales para empresas en América Latina.
3. La estructura debe seguir estrictamente este esquema en Markdown:

# {titulo}

## 🎯 Ganchos de Apertura (Hook Options)
(Redacta 3 opciones verbales completas:
1. Según la técnica de gancho ({gancho}).
2. Una pregunta provocadora directa a fundadores/directivos.
3. Un contraste contraintuitivo de mercado o datos.)

## 📝 Guion y Estructura Editorial ({formato})
(Desarrolla el contenido completo según el formato:
- Si es video_corto: segundo a segundo (0-5s gancho, 5-20s problema/costo, 20-45s demostración de solución, 45-60s conclusión ejecutiva y CTA).
- Si es carrusel: Slide por slide con títulos, textos concisos y llamados visuales.
- Si es hilo: Tweet por tweet numerado (1/6 a 6/6) con gancho, contexto, datos y CTA.
- Si es artículo: Titular, entradilla ejecutiva, subtítulos H2 con desarrollo profundo y lecciones tácticas.)

## 💼 Ángulo Ejecutivo 30X (Audiencia LatAm)
(Explica con claridad la oportunidad de negocio, ahorro en infraestructura o mitigación de riesgo corporativo.)

## 🔍 Evidencia y Fuentes de Respaldo
(Lista los enlaces con una breve anotación del hallazgo.)

## 📋 Notas de Producción
(Tono, sugerencias visuales de pantalla/B-roll y 4 hashtags recomendados.)

Entrega exclusivamente el documento Markdown formateado.
"""

    # 1. Probar Gemini si está configurado
    if api_key and (provider == "gemini" or api_key.startswith("AIzaSy")):
        gemini_model = "gemini-2.5-flash" if "gemini" in model else model
        res = _generate_with_gemini(prompt, api_key, model=gemini_model)
        if res:
            logger.info("Borrador generado exitosamente con Gemini (%s) para '%s'", gemini_model, titulo)
            return res

    # 2. Probar OpenAI / DeepSeek / Groq si está configurado
    openai_key = os.getenv("OPENAI_API_KEY") or (api_key if provider in ("openai", "deepseek", "groq") else None)
    if openai_key and not openai_key.startswith("sk-placeholder"):
        base_urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com",
            "groq": "https://api.groq.com/openai/v1",
        }
        base_url = base_urls.get(provider, "https://api.openai.com/v1")
        res = _generate_with_openai_compatible(prompt, openai_key, base_url, model)
        if res:
            logger.info("Borrador generado exitosamente con %s para '%s'", provider, titulo)
            return res

    # 3. Fallback determinista contextual de alta calidad
    logger.info("Generando borrador con motor editorial determinista para '%s'", titulo)
    return _generate_deterministic_draft(titulo, formato, gancho, evidencia, narrative_context, autor)


def _generate_deterministic_draft(
    titulo: str,
    formato: str,
    gancho: str,
    evidencia: List[str],
    narrative_context: Optional[Dict[str, Any]] = None,
    autor: str = "30X Media",
) -> str:
    """Alias para el generador determinista."""
    return _generate_draft_deterministic(titulo, formato, gancho, evidencia, narrative_context, autor)
