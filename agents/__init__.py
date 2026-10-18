"""Módulo de Agentes Inteligentes con Memoria Narrativa para Radar30X.

Arquitectura:
- ExplorerAgent: Recolección e ingesta multi-fuente pública.
- HistorianAgent: Consulta de memoria 90d, novedad, cálculo de pico y fases temporales.
- CriticAgent: Auditoría de evidencia, veracidad, anti-humo y evaluación sin alucinaciones.
"""

from agents.base import Agent, AgentResult, Narrative, RunContext, Verdict
from agents.explorer import ExplorerAgent
from agents.historian import HistorianAgent
from agents.critic import CriticAgent

__all__ = [
    "Agent",
    "AgentResult",
    "RunContext",
    "Narrative",
    "Verdict",
    "ExplorerAgent",
    "HistorianAgent",
    "CriticAgent",
]
