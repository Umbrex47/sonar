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
    """Perfil completo de estilo, narrativa, palabras clave y fórmulas extraídas del recurso."""

    source_id: str
    modo_extraccion: Literal["ganchos", "keywords", "completo"] = "completo"
    hook: Optional[HookAnalysis] = None
    estructura_narrativa: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Etapas narrativas del contenido (ej: Hook 0-15s, Tensión 15-45s, Payoff 45-90s, CTA)",
    )
    tono_y_voz: str = Field(
        default="autoridad ejecutiva",
        description="Tono predominante (ej: provocador, analítico, de autoridad ejecutiva, conversacional ágil)",
    )
    conceptos_clave: List[str] = Field(default_factory=list)
    palabras_clave: List[str] = Field(
        default_factory=list,
        description="Palabras clave principales y términos de alto valor detectados",
    )
    palabras_clave_secundarias: List[str] = Field(
        default_factory=list,
        description="Palabras clave long-tail o secundarias",
    )
    entidades_detectadas: List[str] = Field(
        default_factory=list,
        description="Modelos de IA, frameworks, herramientas o empresas detectadas",
    )
    enfoques_radar_sugeridos: List[str] = Field(
        default_factory=list,
        description="Términos de búsqueda recomendados para alimentar Radar30X",
    )
    texto_extraido: Optional[str] = Field(
        default=None,
        description="Texto visible extraído de la imagen (OCR) o transcripción clave",
    )
    plantillas_30x: List[str] = Field(
        default_factory=list,
        description="Fórmulas de redacción listas para que 30X las utilice con nuevas noticias",
    )
    resumen_ejecutivo: str = Field(default="")


class KnowledgeSource(BaseModel):
    """Representa un recurso multimedia (video, imagen o archivo) registrado en la base de conocimiento."""

    id: str
    tipo: Literal["youtube", "video", "image", "image_pool", "file", "url", "texto"] = "youtube"
    modo_extraccion: Literal["ganchos", "keywords", "completo"] = "completo"
    url_o_path: str
    imagen_preview: Optional[str] = Field(
        default=None,
        description="URL o Data URI (base64) para previsualizar la imagen o miniatura principal",
    )
    imagenes_pool: List[str] = Field(
        default_factory=list,
        description="Lista de imágenes (Data URIs o URLs) cuando se envía un pool de imágenes",
    )
    total_imagenes: int = Field(default=1, description="Total de imágenes procesadas en este recurso")
    titulo: str
    autor: str = "Desconocido"
    duracion_segundos: float = 0.0
    solicitud_usuario: str = Field(
        description="Solicitud o intención adjunta por el usuario (ej: 'extraer palabras clave sobre agentes')"
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
