"""Modelos de datos para la Base de Conocimiento Vectorial y Extracción de Ganchos."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class HookAnalysis(BaseModel):
    """Análisis detallado del estilo de gancho (primeros 5-15 segundos)."""

    tipo_gancho: str = Field(
        description="Tipo de gancho (dato_contraintuitivo, pregunta_quiebre, afirmacion_audaz, historia_personal, contraste)"
    )
    texto_primeros_15s: str = Field(
        description="Texto transcrito literal de los primeros 15 segundos del recurso"
    )
    analisis_gancho: str = Field(
        description="Explicación del porqué este gancho capta la atención y qué mecanismo psicológico utiliza"
    )
    plantilla_reutilizable: str = Field(
        description="Fórmula o plantilla para adaptar este gancho a cualquier tendencia de IA"
    )


class KnowledgeProfile(BaseModel):
    """Perfil completo de estilo, narrativa y fórmulas extraídas del recurso."""

    source_id: str
    hook: HookAnalysis
    estructura_narrativa: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Etapas narrativas del contenido (ej: Hook 0-15s, Tensión 15-45s, Payoff 45-90s, CTA)",
    )
    tono_y_voz: str = Field(
        description="Tono predominante (ej: provocado, analítico, de autoridad ejecutiva, conversacional ágil)"
    )
    conceptos_clave: List[str] = Field(default_factory=list)
    plantillas_30x: List[str] = Field(
        default_factory=list,
        description="Fórmulas de redacción listas para que 30X las utilice con nuevas noticias",
    )
    resumen_ejecutivo: str = Field(default="")


class KnowledgeSource(BaseModel):
    """Representa un recurso multimedia (video o archivo) registrado en la base de conocimiento."""

    id: str
    tipo: Literal["youtube", "file", "url", "texto"] = "youtube"
    url_o_path: str
    titulo: str
    autor: str = "Desconocido"
    duracion_segundos: float = 0.0
    solicitud_usuario: str = Field(
        description="Solicitud o intención adjunta por el usuario (ej: 'extraer estilo de gancho contraintuitivo')"
    )
    transcripcion_resumen: str = Field(default="")
    creado_en: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    perfil: Optional[KnowledgeProfile] = None


class KnowledgeChunk(BaseModel):
    """Fragmento de transcripción indexado con vector semántico."""

    id: str
    source_id: str
    chunk_index: int
    timestamp_inicio: float = 0.0
    timestamp_fin: float = 0.0
    texto: str
    embedding: List[float] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata_extra: Dict[str, Any] = Field(default_factory=dict)
