"""Ingestor para capturas manuales asistidas desde archivo CSV.

Implementa la estrategia "comunidad como sensor" para integrar contenido público
de plataformas cerradas (LinkedIn, Instagram, TikTok) sin violar términos de servicio,
sin scraping con login y sin almacenar datos personales sensibles.
"""

import csv
import hashlib
import logging
import os
from typing import List, Optional

from sources.base import BaseSource, RawItem

logger = logging.getLogger(__name__)


class ManualCSVSource(BaseSource):
    """Adaptador para cargar contenido capturado manualmente por el equipo editorial."""

    name: str = "ManualCSV"

    def __init__(self, file_path: Optional[str] = None, timeout: float = 5.0) -> None:
        super().__init__(timeout=timeout)
        self.file_path = file_path or os.getenv("MANUAL_CSV_PATH", "data/manual.csv")

    def fetch(self, limit: int = 100) -> List[RawItem]:
        """Lee y valida las filas del archivo CSV de captura asistida."""
        items: List[RawItem] = []
        if not os.path.exists(self.file_path):
            logger.warning("Archivo de captura manual '%s' no encontrado.", self.file_path)
            return items

        try:
            with open(self.file_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fuente_plataforma = (row.get("fuente") or "Manual").strip()
                    titulo = (row.get("titulo") or "").strip()
                    if not titulo:
                        continue

                    url = (row.get("url") or "").strip()
                    resumen = (row.get("resumen") or "").strip()
                    autor = (row.get("autor") or "Autor anónimo").strip()
                    fecha = (row.get("fecha") or "").strip()
                    formato = (row.get("formato_observado") or "articulo").strip()

                    try:
                        vistas = int(row.get("vistas") or 0)
                    except ValueError:
                        vistas = 0

                    try:
                        reacciones = int(row.get("reacciones") or 0)
                    except ValueError:
                        reacciones = 0

                    try:
                        comentarios = int(row.get("comentarios") or 0)
                    except ValueError:
                        comentarios = 0

                    item_id = hashlib.sha256(f"manual:{url or titulo}".encode()).hexdigest()[:16]

                    items.append(
                        RawItem(
                            id=item_id,
                            fuente=f"{fuente_plataforma} (Captura)",
                            titulo=titulo,
                            resumen=resumen,
                            url=url,
                            autor=autor,
                            fecha=fecha,
                            metricas={
                                "vistas": vistas,
                                "reacciones": reacciones,
                                "comentarios": comentarios,
                                "interacciones_totales": vistas + reacciones + comentarios,
                                "formato": formato,
                            },
                        )
                    )
        except Exception as exc:
            logger.error("Error al procesar CSV manual '%s': %s", self.file_path, exc)

        logger.info("ManualCSV: %d ítems cargados desde '%s'.", len(items), self.file_path)
        return items
