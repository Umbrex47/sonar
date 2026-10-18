"""Módulo de conexión con modelos ligeros para preguntas abiertas (Nivel T1 / T2 RAG).

Permite responder preguntas complejas, exploratorias o estratégicas que trascienden
las 6 plantillas fijas T0, fundamentando las respuestas en el grafo de Tarjetas de Narrativa
(narrative_cards) y la memoria histórica de 90 días de Radar30X.

Jerarquía de ejecución:
1. Ollama local (si está activo en http://localhost:11434 con qwen/llama/gemma) -> T1 ($0 marginal).
2. Google Gemini Flash (gemini-2.5-flash / gemini-2.0-flash-lite con LLM_API_KEY) -> T1/T2 (alta velocidad).
3. Proveedor OpenAI compatible (Groq / DeepSeek / OpenRouter) si está configurado en .env.
4. Sintetizador contextual determinista como salvaguarda ante falta de red o cuota.
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

from pipeline.db import Database
from pipeline.knowledge.vector_store import VectorStore

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Consultor Senior de Inteligencia Editorial y Estratégica en IA de Sonar.
Tu misión es asesorar a directivos, CEOs, CTOs y creadores de contenido técnico en Latinoamérica con respuestas concisas, pragmáticas y de alto impacto empresarial.

REGLAS DE RESPUESTA:
1. Enfoque Ejecutivo LatAm: Prioriza retorno de inversión (ROI), mitigación de dependencia en proveedores propietarios (vendor lock-in), costos de inferencia y casos de uso aplicables.
2. Basado en Evidencia Real: Fundamenta tus argumentos en las Tarjetas de Narrativa y métricas provistas en el contexto de Sonar (fases evolutivas, ganchos, veredictos críticos).
3. Anti-Humo: Distingue claramente entre avances demostrados con código/benchmarks abiertos y promesas comerciales exageradas.
4. Formato Estructurado: Usa Markdown limpio con subtítulos H3 (###), viñetas concisas y llamadas tácticas a la acción.
5. Cita las fuentes o proyectos relevantes mencionados en el contexto.
"""


def retrieve_relevant_cards(
    pregunta: str,
    db: Optional[Database] = None,
    top_k: int = 4,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Recupera las tarjetas de narrativa más relevantes para la pregunta del usuario.

    Retorna:
        Tuple[List[Dict], List[str]]: (lista de tarjetas recuperadas, lista de URLs de fuentes)
    """
    db = db or Database()
    cards = db.get_all_narrative_cards()

    if not cards:
        return [], []

    # Tokenizar pregunta
    p_tokens = set(re.findall(r"\b\w{3,}\b", pregunta.lower()))
    scored_cards: List[Tuple[float, Dict[str, Any]]] = []

    # Si hay VectorStore disponible, combinamos similitud vectorial con solapamiento léxico
    vs = None
    q_vec = None
    try:
        vs = VectorStore()
        q_vec = vs.generate_embedding(pregunta)
    except Exception as ex:
        logger.debug("VectorStore no disponible para embeddings de consulta: %s", ex)

    for c in cards:
        text = c.get("texto", "")
        text_lower = text.lower()
        score = 0.0

        # 1. Puntuación por coincidencia de palabras clave
        c_tokens = set(re.findall(r"\b\w{3,}\b", text_lower))
        overlap = len(p_tokens.intersection(c_tokens))
        score += overlap * 1.5

        # 2. Puntuación vectorial si la tarjeta tiene embedding almacenado
        blob = c.get("embedding")
        if blob and vs and q_vec:
            try:
                card_vec = vs.unpack_embedding(blob)
                dot = sum(a * b for a, b in zip(q_vec, card_vec))
                score += max(0.0, dot) * 3.0
            except Exception:
                pass

        # Bonus si contiene menciones directas en el título/tema
        for token in p_tokens:
            if token in text_lower[:80]:
                score += 2.0

        scored_cards.append((score, c))

    # Ordenar descendente por relevancia
    scored_cards.sort(key=lambda x: x[0], reverse=True)
    selected = [c for _, c in scored_cards[:top_k]]

    # Extraer URLs de fuentes de las tarjetas seleccionadas
    extracted_sources: List[str] = []
    for c in selected:
        txt = c.get("texto", "")
        urls = re.findall(r"https?://[^\s\|]+", txt)
        for u in urls:
            u_clean = u.rstrip(".,;)")
            if u_clean not in extracted_sources:
                extracted_sources.append(u_clean)

    return selected, extracted_sources


def _query_ollama(
    prompt: str,
    model: str = "qwen2.5:1.5b",
    base_url: str = "http://localhost:11434",
    timeout: float = 1.0,
) -> Optional[str]:
    """Consulta a una instancia local de Ollama si está disponible."""
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
    except Exception as ex:
        logger.debug("Ollama no disponible en %s: %s", base_url, ex)
    return None


def _query_gemini(
    prompt: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    timeout: float = 15.0,
) -> Optional[str]:
    """Consulta al modelo ligero Gemini Flash mediante API REST oficial con fallback automático."""
    models_to_try = [model]
    if model != "gemini-2.5-flash":
        models_to_try.append("gemini-2.5-flash")
    if "gemini-flash-latest" not in models_to_try:
        models_to_try.append("gemini-flash-latest")

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=timeout, trust_env=False) as client:
                resp = client.post(
                    url,
                    json={
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}],
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0.35,
                            "maxOutputTokens": 2048,
                        },
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
                else:
                    logger.warning("Gemini API retornó status %s para modelo %s: %s", resp.status_code, m, resp.text[:180])
        except Exception as ex:
            logger.warning("Error al conectar con Gemini Flash (%s): %s", m, ex)
    return None


def _query_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    timeout: float = 15.0,
) -> Optional[str]:
    """Consulta a un endpoint compatible con OpenAI (Groq, DeepSeek, OpenRouter)."""
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
    except Exception as ex:
        logger.warning("Error en proveedor OpenAI compatible: %s", ex)
    return None


def _deterministic_open_fallback(
    pregunta: str,
    cards: List[Dict[str, Any]],
    sources: List[str],
) -> str:
    """Generador determinista de síntesis ejecutiva cuando no hay LLM en línea."""
    card_bullets = []
    for c in cards[:3]:
        txt = c.get("texto", "")
        partes = txt.split("|")
        titulo = partes[0].strip() if partes else "Tendencia Emergente"
        fase_match = re.search(r"fase:\s*([^\|]+)", txt)
        fase = fase_match.group(1).strip() if fase_match else "activa"
        gancho_match = re.search(r"gancho dominante:\s*([^\|]+)", txt)
        gancho = gancho_match.group(1).strip() if gancho_match else "analítico"

        card_bullets.append(f"- **{titulo}** *(Fase: `{fase}` | Gancho: `{gancho}`)*")

    bullets_str = "\n".join(card_bullets) if card_bullets else "- Señales emergentes de IA en análisis continuo."

    fallback_text = (
        f"### 💡 Análisis Estratégico Sonar\n\n"
        f"En respuesta a su consulta: *\"{pregunta}\"*:\n\n"
        f"De acuerdo con los datos consolidados y auditados en el Radar de Inteligencia Sonar, "
        f"las señales y arquitecturas con mayor tracción empírica relacionada son:\n\n"
        f"{bullets_str}\n\n"
        f"### 💼 Recomendaciones para Directivos y Creadores LatAm:\n"
        f"1. **Priorice la eficiencia de costos:** Implementar modelos locales o destilados permite reducciones de hasta 80% en costos de inferencia frente a modelos propietarios.\n"
        f"2. **Mitigación de riesgos de gobernanza:** Establecer capas de aislamiento (sandboxing) y trazabilidad estricta antes de desplegar agentes con ejecución de herramientas en producción.\n"
        f"3. **Estrategia editorial:** Articule casos de estudio comparativos con métricas medibles a 90 días en lugar de noticias conceptuales abstractas.\n\n"
        f"*Nota del Sistema: Esta respuesta fue generada con el motor sintético determinista RAG de Sonar.*"
    )
    return fallback_text


def answer_open_question(
    pregunta: str,
    db: Optional[Database] = None,
    force_level: Optional[str] = None,
    show_sources: bool = True,
    ground_truth: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Punto de entrada principal para responder consultas con modelo LLM (Gemini Flash) y RAG."""
    start_time = time.time()
    db = db or Database()

    # 1. Recuperar contexto relevante de las Tarjetas de Narrativa
    relevant_cards, extracted_sources = retrieve_relevant_cards(pregunta, db=db, top_k=4)

    # Incorporar fuentes del ground truth determinista si están presentes
    if ground_truth and ground_truth.get("fuentes"):
        for f in ground_truth["fuentes"]:
            if f and f not in extracted_sources:
                extracted_sources.append(f)

    # 2. Obtener resumen del reporte oficial más reciente
    report_context_lines = []
    latest_rep = db.get_latest_report()
    if latest_rep:
        semana = latest_rep.get("semana", "Actual")
        top_temas = latest_rep.get("top_temas", [])
        report_context_lines.append(f"REPORTE OFICIAL ACTIVO DE SONAR (Semana {semana}):")
        for i, t in enumerate(top_temas[:6]):
            pos = t.get("posicion", i + 1)
            tema = t.get("tema", "")
            fase = t.get("fase", "emergente")
            gancho = t.get("gancho", "analítico")
            crec = t.get("crecimiento", "N/D")
            por_que = t.get("por_que", "")
            report_context_lines.append(
                f"- #{pos} {tema} [Fase: {fase}, Gancho: {gancho}, Crecimiento: {crec}]. Razón: {por_que}"
            )
    report_context_str = "\n".join(report_context_lines)

    # 3. Contexto estructurado de ground truth (si la intención era determinista)
    gt_str = ""
    if ground_truth and ground_truth.get("respuesta"):
        gt_str = f"\nDATOS EXACTOS AUDITADOS DE LA CONSULTA (Ground Truth SQL):\n{ground_truth['respuesta']}\n"

    # 4. Contexto de tarjetas de memoria histórica
    context_chunks = []
    for idx, c in enumerate(relevant_cards, 1):
        context_chunks.append(f"[Tarjeta #{idx}]: {c.get('texto', '')}")

    cards_str = "\n".join(context_chunks) if context_chunks else "Grafo de señales y tendencias de IA de Sonar."

    prompt_to_model = (
        f"{report_context_str}\n"
        f"{gt_str}\n"
        f"TARJETAS DE MEMORIA NARRATIVA Y EVIDENCIA:\n"
        f"{cards_str}\n\n"
        f"PREGUNTA DEL USUARIO:\n"
        f"{pregunta}\n\n"
        f"Por favor, responde de forma clara, directa, ejecutiva y estructurada en Markdown (puedes usar listas, subtítulos y citas concisas si aplica), adaptada para líderes de tecnología y creadores en Latinoamérica."
    )

    respuesta_text: Optional[str] = None
    modelo_usado = "deterministic-fallback"
    nivel_asignado = force_level or "T1"

    # 5. Intentar Ollama Local si está disponible
    ollama_model = os.getenv("LOCAL_MODEL", "qwen2.5:1.5b")
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    if force_level != "T2":
        respuesta_text = _query_ollama(prompt_to_model, model=ollama_model, base_url=ollama_host)
        if respuesta_text:
            modelo_usado = f"ollama:{ollama_model}"
            nivel_asignado = "T1"

    # 6. Si Ollama no está disponible, usar Gemini Flash
    if not respuesta_text:
        gemini_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
        gemini_model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        if gemini_key:
            respuesta_text = _query_gemini(prompt_to_model, api_key=gemini_key, model=gemini_model)
            if respuesta_text:
                modelo_usado = gemini_model
                nivel_asignado = "T1" if "flash" in gemini_model else "T2"

    # 7. Si Gemini no respondió, probar proveedor OpenAI compatible
    if not respuesta_text:
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key and not openai_key.startswith("sk-placeholder"):
            openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            respuesta_text = _query_openai_compatible(
                prompt_to_model, api_key=openai_key, base_url=openai_base, model=openai_model
            )
            if respuesta_text:
                modelo_usado = openai_model
                nivel_asignado = "T1"

    # 8. Fallback determinista de alta fidelidad si ningún LLM respondió
    if not respuesta_text:
        if ground_truth and ground_truth.get("respuesta"):
            respuesta_text = ground_truth["respuesta"]
            modelo_usado = "sonar-sql-ground-truth"
            nivel_asignado = "T0"
        else:
            respuesta_text = _deterministic_open_fallback(pregunta, relevant_cards, extracted_sources)
            modelo_usado = "sonar-rag-synthesizer"
            nivel_asignado = "T0"

    latencia_ms = round((time.time() - start_time) * 1000, 1)

    result = {
        "respuesta": respuesta_text,
        "nivel": nivel_asignado,
        "modelo": modelo_usado,
        "intencion": "pregunta_abierta",
        "fuentes": extracted_sources if show_sources else [],
        "confianza": 0.96 if modelo_usado not in ("sonar-rag-synthesizer", "sonar-sql-ground-truth") else 0.88,
        "escalado": nivel_asignado in ("T1", "T2"),
        "razon_escalado": f"Consulta atendida mediante modelo LLM '{modelo_usado}' con RAG.",
        "latencia_ms": latencia_ms,
        "tarjetas_recuperadas": len(relevant_cards),
    }

    return result
