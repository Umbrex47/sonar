"""Contratos base, protocolos y modelos para la arquitectura de agentes de Radar30X.

Define la interfaz común de cada agente (Explorador, Historiador, Crítico)
y los tipos de datos intercambiados en el ciclo de descubrimiento.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field

from sources.base import RawItem


@dataclass
class RunContext:
    """Contexto de ejecución inmutable y compartido durante un ciclo o backfill."""

    run_id: str
    db: Any  # Instancia de Database
    kind: str = "cycle"  # "cycle" | "backfill"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    items: List[RawItem] = field(default_factory=list)
    clusters: List[Any] = field(default_factory=list)
    narratives: List[Any] = field(default_factory=list)
    verdicts: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Resultado devuelto por la ejecución de un agente con telemetría de auditoría."""

    ok: bool
    agent_name: str
    items: List[Any] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


class Agent(Protocol):
    """Protocolo que debe implementar todo agente del radar."""

    name: str

    def run(self, ctx: RunContext) -> AgentResult:
        """Ejecuta el trabajo del agente dentro del contexto dado."""
        ...


class Narrative(BaseModel):
    """Evolución de una narrativa a lo largo del tiempo (construida por el Agente Historiador)."""

    id: str
    tema: str
    items: List[RawItem] = Field(default_factory=list)
    first_seen: str
    last_seen: str
    fase: str  # "emergente" | "crecimiento" | "saturado" | "resurgente"
    novelty: float = 1.0  # 1 - max_similitud_historica
    recurrencia: int = 1  # Número de semanas distintas con presencia
    pico_fecha: Optional[str] = None
    semanas_desde_pico: int = 0
    ratio_copias: float = 0.0  # Ratio de piezas casi idénticas en 48h
    fuentes_distintas: int = 1
    sparkline: str = ".:oO*"  # Visualización compacta de evolución temporal
    menciones_historicas: List[int] = Field(default_factory=list)
    score_historico: float = 0.0


class Verdict(BaseModel):
    """Veredicto de auditoría de veracidad y anti-humo (emitido por el Agente Crítico)."""

    narrative_id: str
    veracidad_p: float = Field(ge=0.0, le=1.0)
    impacto_real: float = Field(ge=0.0, le=1.0)
    humo_p: float = Field(ge=0.0, le=1.0)
    veredicto: str  # "valido" | "dudoso" | "descartado"
    razones: List[str] = Field(default_factory=list)
    fuentes_verificadas: List[str] = Field(default_factory=list)
    tiene_fuente_primaria: bool = False
    penalidad_clickbait: float = 0.0
    evaluado_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
