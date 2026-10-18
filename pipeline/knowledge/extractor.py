"""Extractor de ganchos, palabras clave, entidades y perfiles de estilo con soporte multimodal."""

from collections import Counter
import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from pipeline.knowledge.models import (
    HookAnalysis,
    KnowledgeChunk,
    KnowledgeProfile,
    KnowledgeSource,
)
from pipeline.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Diccionario curado de entidades de IA, herramientas y empresas relevantes
KNOWN_ENTITIES = [
    "DeepSeek", "DeepSeek R1", "OpenAI", "Anthropic", "Claude 3.5 Sonnet", "Claude 3.7",
    "ChatGPT", "o1", "o3", "GPT-4o", "Cursor", "Windsurf", "Devin", "Replit", "Copilot",
    "HuggingFace", "Meta", "Llama 3", "Gemini", "Mistral", "Qwen", "LangChain", "CrewAI",
    "AutoGPT", "MCP", "Docker", "PyTorch", "Kubernetes", "Linux", "Nvidia", "Groq",
    "Startups LatAm", "AWS", "Microsoft Copilot", "Apple Intelligence"
]

COMMON_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por",
    "con", "no", "una", "su", "para", "es", "al", "lo", "como", "más", "pero", "sus",
    "le", "ya", "o", "este", "sí", "porque", "esta", "entre", "cuando", "muy", "sin",
    "sobre", "también", "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos",
    "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante",
    "ellos", "e", "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras",
    "otra", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual",
    "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú",
    "the", "and", "to", "of", "a", "in", "is", "that", "for", "it", "as", "was", "with",
    "be", "by", "on", "not", "he", "at", "this", "are", "from", "or", "an", "they"
}


def extract_keywords_and_entities_heuristic(
    text: str,
    solicitud: str,
    titulo: str,
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Extrae palabras clave primarias, secundarias, entidades y sugerencias de radar de forma determinista."""
    combined = f"{titulo} {solicitud} {text}".lower()

    # 1. Detectar entidades conocidas
    entidades_encontradas: List[str] = []
    for ent in KNOWN_ENTITIES:
        if re.search(rf"\b{re.escape(ent.lower())}\b", combined):
            entidades_encontradas.append(ent)

    # 2. Tokenizar palabras y contar frecuencias
    title_words = re.findall(r"\b[a-záéíóúñA-ZÁÉÍÓÚÑ0-9\-\.]{3,}\b", f"{titulo} {solicitud}".lower())
    title_tokens = [w for w in title_words if w not in COMMON_STOPWORDS and not w.isdigit()]

    raw_words = re.findall(r"\b[a-záéíóúñA-ZÁÉÍÓÚÑ0-9\-\.]{4,}\b", text.lower())
    filtered_words = [
        w for w in raw_words
        if w not in COMMON_STOPWORDS and not w.isdigit() and len(w) > 3
    ]

    word_counts = Counter(filtered_words)
    # Impulsar términos presentes en título y solicitud
    for tw in title_tokens:
        word_counts[tw] += 6

    keywords_list: List[str] = []
    # Primero las entidades
    for e in entidades_encontradas:
        if e not in keywords_list:
            keywords_list.append(e)

    # Luego palabras más frecuentes basadas en el contenido real
    for w, _ in word_counts.most_common(25):
        w_cap = w.capitalize()
        if w_cap not in keywords_list and len(keywords_list) < 12:
            keywords_list.append(w_cap)

    # Palabras secundarias
    secundarias: List[str] = [
        w.capitalize() for w, _ in word_counts.most_common(40)[12:28]
        if w.capitalize() not in keywords_list
    ]

    # Enfoques sugeridos para Radar30X
    radar_suggestions: List[str] = []
    if any("deepseek" in k.lower() or "razonamiento" in k.lower() for k in keywords_list):
        radar_suggestions.append("Modelos de Razonamiento Open Source y SLMs")
    if any("agente" in k.lower() or "rpa" in k.lower() for k in keywords_list):
        radar_suggestions.append("Agentes Autónomos y Reemplazo de RPA en Empresas")
    if any("seguridad" in k.lower() or "sandbox" in k.lower() for k in keywords_list):
        radar_suggestions.append("Ciberseguridad y Sandboxing para Agentes de IA")
    if any("costo" in k.lower() or "roi" in k.lower() or "operacion" in k.lower() for k in keywords_list):
        radar_suggestions.append("Casos de ROI Corporativo de IA en < 90 Días")

    if not radar_suggestions and keywords_list:
        radar_suggestions.append(f"Adopción Estratégica de {keywords_list[0]} en Empresas")

    return (
        keywords_list[:12],
        secundarias[:10],
        entidades_encontradas[:8],
        radar_suggestions[:4],
    )


def extract_knowledge_profile(
    source_id: str,
    titulo: str,
    transcript_text: str,
    segments: List[Dict[str, Any]],
    solicitud_usuario: str,
    modo: str = "completo",  # "ganchos" | "keywords" | "completo"
    image_data: Optional[str] = None,
    tipo: str = "youtube",
) -> KnowledgeProfile:
    """Extrae perfil de conocimiento según el modo seleccionado: ganchos, palabras clave o completo."""
    first_15s_segments = [s for s in segments if s.get("start", 0.0) <= 20.0]
    first_15s_text = " ".join([s["text"] for s in first_15s_segments]) if first_15s_segments else transcript_text[:250]

    api_key = os.getenv("OPENAI_API_KEY")
    system_instruction = (
        "Eres el analista de inteligencia de contenido y narrativa de 30X, "
        "medio líder de IA para directivos en Latinoamérica. "
        "Analiza el recurso y responde estrictamente con un JSON según las instrucciones y el modo solicitado."
    )

    prompt_text = f"""MODO DE ANÁLISIS: {modo.upper()}
SOLICITUD ESPECÍFICA DEL USUARIO:
"{solicitud_usuario}"

TÍTULO DEL CONTENIDO:
"{titulo}"

TEXTO / TRANSCRIPCIÓN DEL RECURSO:
\"\"\"{transcript_text[:4500]}\"\"\"

Instrucciones por modo:
- Si modo es "keywords": Extrae exhaustivamente las palabras clave principales, secundarias, entidades nombradas (modelos, empresas, herramientas) y temas sugeridos para radar directamente del contenido.
- Si modo es "ganchos": Analiza la psicología de apertura (primeros 15s o elemento visual destacado), tensión, fórmula reutilizable y propuestas para 30X.
- Si modo es "completo": Extrae con máximo detalle tanto los ganchos como las palabras clave y entidades.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{{
  "modo_extraccion": "{modo}",
  "palabras_clave": ["palabra1", "palabra2", "palabra3", "palabra4", "palabra5"],
  "palabras_clave_secundarias": ["termino1", "termino2", "termino3"],
  "entidades_detectadas": ["Entidad o Modelo 1", "Empresa 2", "Herramienta 3"],
  "enfoques_radar_sugeridos": ["Enfoque 1 para Radar30X", "Enfoque 2 para Radar30X"],
  "texto_extraido": "Resumen o texto principal detectado",
  "tipo_gancho": "dato_contraintuitivo | pregunta_quiebre | afirmacion_audaz | historia_personal | contraste",
  "texto_primeros_15s": "{first_15s_text[:200]}",
  "analisis_gancho": "Explicación de por qué este gancho o elemento capta la atención",
  "plantilla_reutilizable": "Fórmula reutilizable lista para usar en nuevos guiones de 30X",
  "estructura_narrativa": [
    {{"etapa": "Hook", "segundos": "0-15s", "proposito": "Captar atención inmediata"}},
    {{"etapa": "Tensión", "segundos": "15-45s", "proposito": "Presentar el problema real en las empresas"}},
    {{"etapa": "Payoff", "segundos": "45-90s", "proposito": "Demostración o dato de solución"}},
    {{"etapa": "CTA", "segundos": "Final", "proposito": "Llamada a la acción"}}
  ],
  "tono_y_voz": "autoridad ejecutiva | provocador y directo | analítico de producto",
  "conceptos_clave": ["concepto1", "concepto2", "concepto3"],
  "plantillas_30x": [
    "Fórmula 1 de adaptación para 30X",
    "Fórmula 2 de adaptación para 30X"
  ],
  "resumen_ejecutivo": "Síntesis en 2 oraciones del recurso"
}}
"""
    parsed: Optional[Dict[str, Any]] = None

    # 1. Intentar con Gemini (proveedor configurado por defecto con LLM_API_KEY)
    gemini_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    if gemini_key and not gemini_key.startswith("sk-placeholder"):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            full_prompt = f"{system_instruction}\n\n{prompt_text}"
            with httpx.Client(timeout=25.0, trust_env=False) as client:
                res = client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {"response_mime_type": "application/json"},
                    },
                )
                if res.status_code == 200:
                    cand = res.json().get("candidates", [])
                    if cand:
                        raw_json = cand[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(raw_json)
        except Exception as e:
            logger.warning("Fallo al llamar Gemini para perfil (%s): %s", modo, e)

    # 2. Si no disponible o falló, intentar con OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if not parsed and openai_key and not openai_key.startswith("sk-placeholder"):
        try:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            is_image = tipo in ("image", "image_pool") or bool(image_data)
            messages_payload: List[Dict[str, Any]] = [{"role": "system", "content": system_instruction}]
            if is_image and image_data:
                messages_payload.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_data, "detail": "high"}},
                    ],
                })
            else:
                messages_payload.append({"role": "user", "content": prompt_text})

            with httpx.Client(timeout=25.0, trust_env=False) as client:
                res = client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": messages_payload,
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                    },
                )
                if res.status_code == 200:
                    data = res.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(data)
        except Exception as e:
            logger.warning("Fallo al llamar OpenAI para perfil (%s): %s", modo, e)

    if parsed:
        hook_obj = None
        if modo in ["ganchos", "completo"] or parsed.get("analisis_gancho"):
            hook_obj = HookAnalysis(
                tipo_gancho=parsed.get("tipo_gancho", "dato_contraintuitivo"),
                texto_primeros_15s=parsed.get("texto_primeros_15s", first_15s_text[:200]),
                analisis_gancho=parsed.get("analisis_gancho", "Gancho de alta retención basado en contraste"),
                plantilla_reutilizable=parsed.get("plantilla_reutilizable", "El [X]% de las empresas cometen el error de [Y]..."),
            )

        return KnowledgeProfile(
            source_id=source_id,
            modo_extraccion=modo,  # type: ignore
            hook=hook_obj,
            estructura_narrativa=parsed.get("estructura_narrativa") or [],
            tono_y_voz=parsed.get("tono_y_voz") or "Autoridad ejecutiva y analítica",
            conceptos_clave=parsed.get("conceptos_clave") or [],
            palabras_clave=parsed.get("palabras_clave") or [],
            palabras_clave_secundarias=parsed.get("palabras_clave_secundarias") or [],
            entidades_detectadas=parsed.get("entidades_detectadas") or [],
            enfoques_radar_sugeridos=parsed.get("enfoques_radar_sugeridos") or [],
            texto_extraido=parsed.get("texto_extraido"),
            plantillas_30x=parsed.get("plantillas_30x") or [],
            resumen_ejecutivo=parsed.get("resumen_ejecutivo") or "",
        )

    # Fallback heurístico determinista y estructurado
    kw_primarias, kw_secundarias, entidades, radar_sug = extract_keywords_and_entities_heuristic(
        transcript_text, solicitud_usuario, titulo
    )

    first_lower = first_15s_text.lower()
    if any(k in first_lower for k in ["por qué", "cómo", "qué pasa si", "sabías"]):
        tipo_gancho = "pregunta_quiebre"
        analisis = f"Gancho socrático que abre un bucle de curiosidad alineado a: '{solicitud_usuario}'."
        plantilla = "¿Por qué las mejores empresas de LatAm están abandonando [Herramienta tradicional] por [Nueva IA]?"
    elif any(k in first_lower for k in ["error", "cuidado", "peligro", "no uses", "falso"]):
        tipo_gancho = "afirmacion_audaz"
        analisis = f"Gancho de aversión a la pérdida y alerta operativa enfocado en: '{solicitud_usuario}'."
        plantilla = "El error número 1 al implementar [Tendencia IA] que le cuesta miles de dólares a tu empresa."
    else:
        tipo_gancho = "dato_contraintuitivo"
        analisis = f"Gancho de contraste que rompe el sentido común y ofrece una perspectiva ejecutiva según: '{solicitud_usuario}'."
        plantilla = "El 90% de los líderes creen que [Mito], pero la realidad en producción es [Dato duro]."

    hook_obj = None
    if modo in ["ganchos", "completo"]:
        hook_obj = HookAnalysis(
            tipo_gancho=tipo_gancho,
            texto_primeros_15s=first_15s_text[:250],
            analisis_gancho=analisis,
            plantilla_reutilizable=plantilla,
        )

    estructura = [
        {"etapa": "Hook", "segundos": "0-15s", "proposito": "Captar atención con dato de ruptura o titular audaz"},
        {"etapa": "Tensión", "segundos": "15-45s", "proposito": "Demostrar el costo oculto de ignorar esta tendencia"},
        {"etapa": "Payoff / Caso", "segundos": "45-90s", "proposito": "Explicar la arquitectura o flujo práctico"},
        {"etapa": "CTA", "segundos": "Final", "proposito": "Invitar al debate estratégico en comentarios"},
    ]

    plantillas_30x = [
        f"Short / Reel: '{plantilla}' + desglose visual en pantalla",
        f"Carrusel LinkedIn: '3 lecciones estratégicas de {titulo} aplicadas a directivos en LatAm'",
    ]

    resumen = (
        f"Recurso analizado en modo '{modo}'. "
        f"Palabras clave clave: {', '.join(kw_primarias[:5])}. "
        f"Orientado a líderes empresariales y equipos de producto."
    )

    return KnowledgeProfile(
        source_id=source_id,
        modo_extraccion=modo,  # type: ignore
        hook=hook_obj,
        estructura_narrativa=estructura if modo in ["ganchos", "completo"] else [],
        tono_y_voz="Autoridad ejecutiva, directo y periodístico",
        conceptos_clave=kw_primarias[:4],
        palabras_clave=kw_primarias,
        palabras_clave_secundarias=kw_secundarias,
        entidades_detectadas=entidades,
        enfoques_radar_sugeridos=radar_sug,
        texto_extraido=transcript_text[:400] if tipo == "image" else None,
        plantillas_30x=plantillas_30x if modo in ["ganchos", "completo"] else [],
        resumen_ejecutivo=resumen,
    )


def extract_hook_and_profile(
    source_id: str,
    titulo: str,
    transcript_text: str,
    segments: List[Dict[str, Any]],
    solicitud_usuario: str,
) -> KnowledgeProfile:
    """Función de compatibilidad con código existente (extrae en modo completo)."""
    return extract_knowledge_profile(
        source_id=source_id,
        titulo=titulo,
        transcript_text=transcript_text,
        segments=segments,
        solicitud_usuario=solicitud_usuario,
        modo="completo",
    )


def build_knowledge_chunks(
    source_id: str,
    segments: List[Dict[str, Any]],
    vector_store: VectorStore,
    profile: Optional[KnowledgeProfile] = None,
    chunk_size_words: int = 80,
) -> List[KnowledgeChunk]:
    """Divide la transcripción en chunks semánticos contiguos e indexa chunks especializados para keywords y ganchos."""
    chunks: List[KnowledgeChunk] = []
    current_words: List[str] = []
    chunk_start = 0.0
    chunk_end = 0.0
    chunk_idx = 0

    # 1. Chunks de la transcripción / texto
    for seg in segments:
        words = seg.get("text", "").split()
        if not words:
            continue

        if not current_words:
            chunk_start = float(seg.get("start", 0.0))

        current_words.extend(words)
        chunk_end = float(seg.get("start", 0.0)) + float(seg.get("duration", 0.0))

        if len(current_words) >= chunk_size_words:
            chunk_text = " ".join(current_words)
            chunk_id = f"{source_id}-chk-{chunk_idx}"
            emb = vector_store.generate_embedding(chunk_text)

            chunks.append(
                KnowledgeChunk(
                    id=chunk_id,
                    source_id=source_id,
                    chunk_index=chunk_idx,
                    timestamp_inicio=round(chunk_start, 2),
                    timestamp_fin=round(chunk_end, 2),
                    texto=chunk_text,
                    embedding=emb,
                    tags=["transcripcion", "conocimiento"],
                )
            )
            chunk_idx += 1
            current_words = current_words[-15:]
            chunk_start = max(0.0, chunk_end - 5.0)

    if current_words:
        chunk_text = " ".join(current_words)
        chunk_id = f"{source_id}-chk-{chunk_idx}"
        emb = vector_store.generate_embedding(chunk_text)
        chunks.append(
            KnowledgeChunk(
                id=chunk_id,
                source_id=source_id,
                chunk_index=chunk_idx,
                timestamp_inicio=round(chunk_start, 2),
                timestamp_fin=round(chunk_end, 2),
                texto=chunk_text,
                embedding=emb,
                tags=["transcripcion", "conocimiento"],
            )
        )
        chunk_idx += 1

    # 2. Chunk semántico especializado de Palabras Clave y Entidades (si profile existe)
    if profile and profile.palabras_clave:
        kw_text = (
            f"Palabras clave y entidades estratégicas: {', '.join(profile.palabras_clave)}. "
            f"Entidades detectadas: {', '.join(profile.entidades_detectadas)}. "
            f"Conceptos y radar: {', '.join(profile.enfoques_radar_sugeridos)}."
        )
        chunks.append(
            KnowledgeChunk(
                id=f"{source_id}-chk-kw",
                source_id=source_id,
                chunk_index=chunk_idx,
                timestamp_inicio=0.0,
                timestamp_fin=0.0,
                texto=kw_text,
                embedding=vector_store.generate_embedding(kw_text),
                tags=["keywords", "entidades", "radar"],
            )
        )
        chunk_idx += 1

    # 3. Chunk semántico especializado de Ganchos (si profile.hook existe)
    if profile and profile.hook:
        hook_text = (
            f"Gancho narrativo ({profile.hook.tipo_gancho}): {profile.hook.plantilla_reutilizable}. "
            f"Análisis: {profile.hook.analisis_gancho}. Texto: {profile.hook.texto_primeros_15s}"
        )
        chunks.append(
            KnowledgeChunk(
                id=f"{source_id}-chk-hook",
                source_id=source_id,
                chunk_index=chunk_idx,
                timestamp_inicio=0.0,
                timestamp_fin=15.0,
                texto=hook_text,
                embedding=vector_store.generate_embedding(hook_text),
                tags=["gancho", "plantilla", "narrativa"],
            )
        )

    return chunks
