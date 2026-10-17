"""Módulo web para Radar de Contenido 30X.

Proporciona servidor HTTP nativo y panel de control web interactivo
para explorar tendencias, decisiones calibradas y referencias/evidencias.
"""

from .server import run_server

__all__ = ["run_server"]
