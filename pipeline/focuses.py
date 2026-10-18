"""Gestión de enfoques de búsqueda dinámicos para Radar30X.

Permite a los directivos y al equipo editorial configurar, activar y añadir
nuevos ángulos y palabras clave de monitoreo (polémicas de OpenAI/Anthropic,
benchmarks de razonamiento, desarrollo personal de CEO, oportunidades de ROI, etc.).
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_FOCUSES_PATH = "data/search_focuses.json"


class SearchFocus(BaseModel):
    """Representa un enfoque o track temático de búsqueda."""

    id: str
    nombre: str
    categoria: str  # polemicas | benchmarks | ceo_liderazgo | oportunidades_roi | agentes_operaciones | seguridad
    descripcion: str
    keywords: List[str]
    activo: bool = True
    creado_en: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


DEFAULT_FOCUSES: List[Dict[str, Any]] = [
    {
        "id": "polemicas-labs",
        "nombre": "Polémicas y Gobernanza en Grandes Labs",
        "categoria": "polemicas",
        "descripcion": "Disputas legales, salidas de ejecutivos, seguridad crítica y tensiones entre OpenAI, Anthropic, Meta y Google.",
        "keywords": [
            "OpenAI", "Anthropic", "Sam Altman", "Dario Amodei", "safety researcher",
            "copyright lawsuit", "antitrust AI", "Replit Anthropic", "whistleblower", "departures"
        ],
        "activo": True,
    },
    {
        "id": "benchmarks-race",
        "nombre": "Benchmarks & Carrera de Modelos de Razonamiento",
        "categoria": "benchmarks",
        "descripcion": "Evolución de capacidades, evaluaciones rigurosas (SWE-bench, MATH, reasoning) y comparativas de costo de inferencia.",
        "keywords": [
            "benchmark", "evals", "SWE-bench", "reasoning models", "o3", "Claude 3.5 Sonnet",
            "DeepSeek v3", "Gemini 2", "token pricing", "costo de inferencia"
        ],
        "activo": True,
    },
    {
        "id": "ceo-desarrollo",
        "nombre": "Desarrollo Personal de CEO & Liderazgo en la Era de IA",
        "categoria": "ceo_liderazgo",
        "descripcion": "Productividad de directores, toma de decisiones con IA, modelos mentales ejecutivos y rediseño de equipos de alto rendimiento.",
        "keywords": [
            "CEO", "tech leadership", "liderazgo tecnológico", "toma de decisiones",
            "productividad directiva", "founder", "cultura corporativa", "gestión de talento", "equipos autónomos"
        ],
        "activo": True,
    },
    {
        "id": "oportunidades-roi",
        "nombre": "Oportunidades de Negocio & Retorno de Inversión (ROI)",
        "categoria": "oportunidades_roi",
        "descripcion": "Casos prácticos de generación de ingresos, ahorro operativo medible e implementación de IA en banca, retail y fintech en LatAm.",
        "keywords": [
            "ROI inteligencia artificial", "reducción de costos", "ahorro operativo",
            "banca IA", "fintech LatAm", "adopción empresarial", "casos de uso monetización"
        ],
        "activo": True,
    },
    {
        "id": "agentes-operaciones",
        "nombre": "Agentes Autónomos y Reemplazo de RPA",
        "categoria": "agentes_operaciones",
        "descripcion": "Automatización operativa de punta a punta, eliminación de software legado y orquestación de workflows.",
        "keywords": [
            "agentes de IA", "reemplazo RPA", "automatización procesos", "workflows autónomos",
            "conciliación", "prospección B2B"
        ],
        "activo": True,
    },
    {
        "id": "seguridad-sandboxing",
        "nombre": "Sandboxing, Seguridad y Cumplimiento Regulatorio",
        "categoria": "seguridad",
        "descripcion": "Aislamiento de comandos de agentes, auditoría legal y gobernanza en contrataciones de talento.",
        "keywords": [
            "sandboxing IA", "jailbreak", "seguridad agentes", "compliance IA",
            "auditoría algoritmos", "ciberseguridad corporativa"
        ],
        "activo": True,
    },
    {
        "id": "agentes-voz-multimodal",
        "nombre": "Agentes de Voz en Tiempo Real & Modelos Multimodales",
        "categoria": "voz_multimodal",
        "descripcion": "Modelos de voz de latencia ultrabaja (<200ms), WebRTC, GPT-4o Realtime, Gemini Live y generación de video comercial.",
        "keywords": [
            "voice agents", "agentes de voz", "WebRTC IA", "GPT-4o Realtime",
            "Gemini Live", "ElevenLabs", "Sora video", "Kling AI", "generación video IA"
        ],
        "activo": True,
    },
    {
        "id": "graphrag-knowledge",
        "nombre": "GraphRAG & Grafos de Conocimiento Empresarial",
        "categoria": "graphrag",
        "descripcion": "Evolución de RAG tradicional hacia grafos de conocimiento estructurados (Neo4j, Microsoft GraphRAG) para eliminar alucinaciones.",
        "keywords": [
            "GraphRAG", "knowledge graphs", "grafos conocimiento", "Neo4j IA",
            "RAG hibrido", "vector graph", "ontologías IA"
        ],
        "activo": True,
    },
    {
        "id": "slms-borde-inferencia",
        "nombre": "Modelos SLM en el Borde & Optimización de Inferencia",
        "categoria": "slms_borde",
        "descripcion": "Despliegue de modelos pequeños (1B-8B) en hardware local, cuantización GGUF/AWQ, vLLM y soberanía de datos.",
        "keywords": [
            "SLM", "inferencia local", "Ollama", "vLLM", "DeepSeek R1 Distill",
            "Qwen 2.5", "Phi-4", "cuantización GGUF", "soberanía de datos"
        ],
        "activo": True,
    },
    {
        "id": "fintech-fraude-ia",
        "nombre": "IA en Finanzas, Prevención de Fraude & Core Bancario",
        "categoria": "fintech_fraude",
        "descripcion": "Detección de anomalías en transacciones en tiempo real, scoring crediticio aumentado y cumplimiento AML en banca de LatAm.",
        "keywords": [
            "prevención de fraude IA", "fintech IA", "scoring crediticio",
            "banca digital", "análisis de riesgo", "AML compliance", "ciberfraude"
        ],
        "activo": True,
    },
    {
        "id": "coding-agents-software",
        "nombre": "Coding Agents & Automatización del Ciclo de Software",
        "categoria": "coding_agents",
        "descripcion": "Herramientas de ingeniería de software autónoma (Claude Code, Cursor, Devin, validación formal) y productividad de desarrolladores.",
        "keywords": [
            "Claude Code", "Cursor AI", "coding agent", "SWE-bench",
            "desarrollo software IA", "agentes programadores", "refactoring autonomo"
        ],
        "activo": True,
    },
]


def _get_storage_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / DEFAULT_FOCUSES_PATH


_IN_MEMORY_FOCUSES: Optional[List[SearchFocus]] = None


def load_focuses(storage_path: Optional[str] = None, force_reload: bool = False) -> List[SearchFocus]:
    """Carga los enfoques de búsqueda desde memoria o archivo JSON de configuración."""
    global _IN_MEMORY_FOCUSES

    if _IN_MEMORY_FOCUSES is not None and not force_reload:
        return list(_IN_MEMORY_FOCUSES)

    path = _get_storage_path(storage_path)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            focuses = [SearchFocus(**item) for item in raw]
            _IN_MEMORY_FOCUSES = list(focuses)
            return focuses
        except Exception as e:
            logger.warning("No se pudo leer %s: %s. Usando defaults.", path, e)

    focuses = [SearchFocus(**f) for f in DEFAULT_FOCUSES]
    save_focuses(focuses, storage_path)
    _IN_MEMORY_FOCUSES = list(focuses)
    return focuses


def save_focuses(focuses: List[SearchFocus], storage_path: Optional[str] = None) -> bool:
    """Persiste la lista de enfoques de búsqueda en el archivo JSON (con respaldo en memoria si es read-only)."""
    global _IN_MEMORY_FOCUSES
    _IN_MEMORY_FOCUSES = list(focuses)

    path = _get_storage_path(storage_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [f.model_dump() for f in focuses]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.debug("Guardado en memoria porque el sistema de archivos es read-only: %s", e)
        return False


def add_focus(
    nombre: str,
    categoria: str,
    keywords: List[str],
    descripcion: str = "",
    storage_path: Optional[str] = None,
) -> SearchFocus:
    """Añade un nuevo enfoque de búsqueda definido por el usuario."""
    focuses = load_focuses(storage_path)
    import re
    # Generar un ID limpio a partir del nombre
    clean_id = re.sub(r"[^a-zA-Z0-9]+", "-", nombre.strip().lower()).strip("-")
    if not clean_id:
        clean_id = f"focus-{int(datetime.now().timestamp())}"

    # Evitar colisión de IDs
    existing_ids = {f.id for f in focuses}
    final_id = clean_id
    counter = 1
    while final_id in existing_ids:
        final_id = f"{clean_id}-{counter}"
        counter += 1

    new_focus = SearchFocus(
        id=final_id,
        nombre=nombre.strip(),
        categoria=categoria.strip() or "general",
        descripcion=descripcion.strip(),
        keywords=[k.strip() for k in keywords if k.strip()],
        activo=True,
    )
    focuses.append(new_focus)
    save_focuses(focuses, storage_path)
    return new_focus


def toggle_focus(focus_id: str, storage_path: Optional[str] = None) -> Optional[SearchFocus]:
    """Alterna el estado activo/inactivo de un enfoque de búsqueda."""
    focuses = load_focuses(storage_path)
    target = None
    for f in focuses:
        if f.id == focus_id:
            f.activo = not f.activo
            target = f
            break
    if target:
        save_focuses(focuses, storage_path)
    return target


def delete_focus(focus_id: str, storage_path: Optional[str] = None) -> bool:
    """Elimina un enfoque de búsqueda por su ID."""
    focuses = load_focuses(storage_path)
    initial_len = len(focuses)
    focuses = [f for f in focuses if f.id != focus_id]
    if len(focuses) < initial_len:
        save_focuses(focuses, storage_path)
        return True
    return False


def get_active_queries() -> List[str]:
    """Genera las consultas de búsqueda optimizadas para los adaptadores de ingesta a partir de los enfoques activos."""
    focuses = load_focuses()
    queries: List[str] = []
    for f in focuses:
        if not f.activo:
            continue
        # Añadir las keywords principales agrupadas
        if f.keywords:
            top_kws = f.keywords[:4]
            queries.append(" OR ".join([f'"{k}"' if " " in k else k for k in top_kws]))
    return queries
