"""Capa de persistencia SQLite para Radar30X.

Gestiona almacenamiento local determinista, ligero y sin dependencias externas
para ítems recolectados, temas agrupados, decisiones calibradas y reportes históricos.
"""

from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from sources.base import RawItem

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/radar.db"


class Database:
    """Administrador de base de datos SQLite para Radar30X."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or os.getenv("RADAR_DB_PATH", DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Retorna una conexión configurada con row_factory a SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Crea las tablas e índices si no existen."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Tabla de ítems sin procesar normalizados
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    fuente TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    resumen TEXT,
                    url TEXT NOT NULL UNIQUE,
                    autor TEXT,
                    fecha TEXT,
                    metricas_json TEXT,
                    creado_en TEXT
                )
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_fuente ON items(fuente)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_fecha ON items(fecha)")

            # Tabla de clusters y temas detectados
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clusters (
                    id TEXT PRIMARY KEY,
                    tema_canonico TEXT NOT NULL,
                    num_items INTEGER DEFAULT 1,
                    fuentes_json TEXT,
                    items_ids_json TEXT,
                    actualizado_en TEXT
                )
            """
            )

            # Tabla de decisiones type-safe tomadas por Jev
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    cluster_id TEXT PRIMARY KEY,
                    fase TEXT NOT NULL,
                    gancho TEXT NOT NULL,
                    formato TEXT NOT NULL,
                    novedad REAL NOT NULL,
                    encaje_audiencia REAL NOT NULL,
                    confianza REAL NOT NULL,
                    score_final REAL DEFAULT 0.0,
                    por_que TEXT,
                    adaptacion_30x TEXT,
                    creado_en TEXT,
                    FOREIGN KEY(cluster_id) REFERENCES clusters(id)
                )
            """
            )

            # Tabla de reportes generados
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    semana TEXT NOT NULL,
                    generado_en TEXT NOT NULL,
                    json_data TEXT NOT NULL
                )
            """
            )
            conn.commit()

    def save_items(self, items: List[RawItem]) -> int:
        """Guarda o actualiza ítems evitando duplicados por URL canónica.

        Returns:
            Número de ítems nuevos insertados.
        """
        if not items:
            return 0

        inserted = 0
        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for it in items:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO items
                        (id, fuente, titulo, resumen, url, autor, fecha, metricas_json, creado_en)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            it.id,
                            it.fuente,
                            it.titulo,
                            it.resumen,
                            it.url,
                            it.autor,
                            it.fecha,
                            json.dumps(it.metricas, ensure_ascii=False),
                            now,
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
            conn.commit()

        logger.debug("Guardados %d ítems en la base de datos.", inserted)
        return inserted

    def get_all_items(self) -> List[RawItem]:
        """Recupera todos los ítems almacenados."""
        items: List[RawItem] = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items ORDER BY fecha DESC")
            for row in cursor.fetchall():
                try:
                    metricas = json.loads(row["metricas_json"] or "{}")
                except json.JSONDecodeError:
                    metricas = {}
                items.append(
                    RawItem(
                        id=row["id"],
                        fuente=row["fuente"],
                        titulo=row["titulo"],
                        resumen=row["resumen"] or "",
                        url=row["url"],
                        autor=row["autor"] or "Desconocido",
                        fecha=row["fecha"] or "",
                        metricas=metricas,
                    )
                )
        return items

    def save_report(self, report_id: str, semana: str, payload: Dict[str, Any]) -> None:
        """Almacena el reporte final en la base de datos."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO reports (id, semana, generado_en, json_data)
                VALUES (?, ?, ?, ?)
                """,
                (report_id, semana, now, json.dumps(payload, ensure_ascii=False, indent=2)),
            )
            conn.commit()
