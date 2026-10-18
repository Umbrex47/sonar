"""Capa de persistencia SQLite para Radar30X.

Gestiona almacenamiento local determinista, ligero y sin dependencias externas
para ítems recolectados, temas agrupados, decisiones calibradas y reportes históricos.
"""

from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

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

            # --- TABLAS DE LA ARQUITECTURA DE AGENTES Y MEMORIA NARRATIVA ---

            # 1. Runs del orquestador (ciclos 12h y backfills)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    kind TEXT NOT NULL, /* cycle | backfill */
                    status TEXT NOT NULL, /* running | completed | failed */
                    stats_json TEXT
                )
            """
            )

            # 2. Narrativas históricas con memoria de 90 días
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS narratives (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    first_seen TEXT,
                    last_seen TEXT,
                    fase TEXT NOT NULL, /* emergente | crecimiento | saturado | resurgente */
                    novelty REAL DEFAULT 1.0,
                    recurrencia INTEGER DEFAULT 1,
                    pico_fecha TEXT,
                    semanas_desde_pico INTEGER DEFAULT 0,
                    ratio_copias REAL DEFAULT 0.0,
                    fuentes_distintas INTEGER DEFAULT 1,
                    sparkline TEXT DEFAULT '',
                    actualizado_en TEXT
                )
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_narratives_fase ON narratives(fase)")

            # 3. Pertenencia de ítems a narrativas con puntaje de similitud
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS narrative_items (
                    narrative_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    similitud REAL DEFAULT 1.0,
                    PRIMARY KEY (narrative_id, item_id),
                    FOREIGN KEY(narrative_id) REFERENCES narratives(id),
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )
            """
            )

            # 4. Serie temporal diaria para tracking de evolución y sparklines
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS narrative_stats_daily (
                    narrative_id TEXT NOT NULL,
                    dia TEXT NOT NULL,
                    menciones INTEGER DEFAULT 0,
                    fuentes_distintas INTEGER DEFAULT 0,
                    engagement_norm REAL DEFAULT 0.0,
                    PRIMARY KEY (narrative_id, dia),
                    FOREIGN KEY(narrative_id) REFERENCES narratives(id)
                )
            """
            )

            # 5. Veredictos del Agente Crítico (sin humo / trazabilidad de veracidad)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS verdicts (
                    narrative_id TEXT PRIMARY KEY,
                    veracidad_p REAL NOT NULL,
                    impacto_real REAL NOT NULL,
                    humo_p REAL NOT NULL,
                    veredicto TEXT NOT NULL, /* valido | dudoso | descartado */
                    razones_json TEXT,
                    evaluado_at TEXT NOT NULL,
                    FOREIGN KEY(narrative_id) REFERENCES narratives(id)
                )
            """
            )

            # 6. Registro de auditoría (audit_log) de cada agente
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    agente TEXT NOT NULL,
                    accion TEXT NOT NULL,
                    payload_json TEXT,
                    ts TEXT NOT NULL
                )
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_agente ON audit_log(agente)")

            # 7. Vectores semánticos de ítems para búsqueda de vecinos en 90 días
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS item_embeddings (
                    item_id TEXT PRIMARY KEY,
                    vector_blob BLOB NOT NULL,
                    dim INTEGER NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )
            """
            )

            # 8. Tarjetas de narrativa materializadas para RAG eficiente
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS narrative_cards (
                    narrative_id TEXT PRIMARY KEY,
                    texto TEXT NOT NULL,
                    embedding BLOB,
                    actualizado_at TEXT NOT NULL
                )
            """
            )

            # 9. Caché de respuestas del chatbot
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS answers_cache (
                    hash TEXT PRIMARY KEY,
                    pregunta TEXT NOT NULL,
                    respuesta_json TEXT NOT NULL,
                    nivel TEXT NOT NULL,
                    creado_at TEXT NOT NULL,
                    invalidado_at TEXT
                )
            """
            )

            # 10. Logs y observabilidad del chatbot
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id TEXT PRIMARY KEY,
                    pregunta TEXT NOT NULL,
                    intencion TEXT,
                    nivel TEXT,
                    modelo TEXT,
                    latencia_ms REAL,
                    escalado INTEGER DEFAULT 0,
                    razon_escalado TEXT,
                    tokens INTEGER DEFAULT 0,
                    coste_usd REAL DEFAULT 0.0,
                    groundedness REAL,
                    ts TEXT NOT NULL
                )
            """
            )

            # 11. Gestor de borradores (espejo relacional de los archivos Markdown)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    narrative_id TEXT,
                    titulo TEXT NOT NULL,
                    formato TEXT NOT NULL,
                    gancho TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'borrador',
                    autor TEXT DEFAULT '30X Media',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    published_url TEXT,
                    metricas_json TEXT,
                    path TEXT NOT NULL
                )
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_drafts_estado ON drafts(estado)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_drafts_narrative ON drafts(narrative_id)")

            # 12. Versiones de borradores para historial y diffs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    contenido TEXT NOT NULL,
                    autor TEXT,
                    ts TEXT NOT NULL,
                    FOREIGN KEY(draft_id) REFERENCES drafts(id)
                )
            """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_draft_versions_draft ON draft_versions(draft_id)")

            # Migraciones seguras para columnas opcionales en items
            for col in ["run_id TEXT", "tema_canonico TEXT"]:
                try:
                    cursor.execute(f"ALTER TABLE items ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass

            conn.commit()

    def save_items(self, items: List[RawItem], run_id: Optional[str] = None) -> int:
        """Guarda o actualiza ítems evitando duplicados por URL canónica.

        Args:
            items: Lista de RawItem a persistir.
            run_id: ID opcional de la ejecución del orquestador.

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
                        (id, fuente, titulo, resumen, url, autor, fecha, metricas_json, creado_en, run_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            run_id,
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
            conn.commit()

        logger.debug("Guardados %d ítems en la base de datos (run_id=%s).", inserted, run_id)
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

    def get_items_history(self, days: int = 90) -> List[Dict[str, Any]]:
        """Recupera ítems históricos dentro de la ventana de días solicitada."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        records: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, fuente, titulo, resumen, url, autor, fecha, metricas_json FROM items WHERE fecha >= ? OR creado_en >= ? ORDER BY fecha DESC",
                (cutoff, cutoff),
            )
            for row in cur.fetchall():
                try:
                    metricas = json.loads(row["metricas_json"] or "{}")
                except json.JSONDecodeError:
                    metricas = {}
                records.append({
                    "id": row["id"],
                    "fuente": row["fuente"],
                    "titulo": row["titulo"],
                    "resumen": row["resumen"] or "",
                    "url": row["url"],
                    "autor": row["autor"] or "Desconocido",
                    "fecha": row["fecha"] or "",
                    "metricas": metricas,
                })
        return records

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

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Recupera el reporte generado más reciente de la tabla reports o desde disco como fallback."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT json_data FROM reports ORDER BY generado_en DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                try:
                    return json.loads(row["json_data"])
                except Exception:
                    pass

        # Fallback a disco en carpeta out/
        import glob
        out_dir = os.environ.get("RADAR_OUT_DIR") or os.path.join(os.path.dirname(os.path.dirname(__file__)), "out")
        report_files = sorted(glob.glob(os.path.join(out_dir, "report_*.json")), reverse=True)
        if report_files:
            try:
                with open(report_files[0], "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    # --- MÉTODOS DE AUDITORÍA Y ORQUESTACIÓN DE AGENTES ---

    def log_audit(self, run_id: str, agente: str, accion: str, payload: Dict[str, Any]) -> None:
        """Registra una acción de un agente en el log de auditoría."""
        import uuid
        log_id = f"aud_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_log (id, run_id, agente, accion, payload_json, ts)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (log_id, run_id, agente, accion, json.dumps(payload, ensure_ascii=False), now),
            )
            conn.commit()

    def start_run(self, run_id: str, kind: str = "cycle") -> None:
        """Registra el inicio de un ciclo de ejecución o backfill."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO runs (id, started_at, kind, status, stats_json)
                VALUES (?, ?, ?, 'running', '{}')
                """,
                (run_id, now, kind),
            )
            conn.commit()

    def finish_run(self, run_id: str, status: str = "completed", stats: Optional[Dict[str, Any]] = None) -> None:
        """Marca un run como completado o fallido registrando sus métricas."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE runs
                SET ended_at = ?, status = ?, stats_json = ?
                WHERE id = ?
                """,
                (now, status, json.dumps(stats or {}, ensure_ascii=False), run_id),
            )
            conn.commit()

    def get_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Recupera las ejecuciones recientes con sus estadísticas."""
        runs: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))
            for row in cur.fetchall():
                try:
                    stats = json.loads(row["stats_json"] or "{}")
                except json.JSONDecodeError:
                    stats = {}
                runs.append({
                    "id": row["id"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "kind": row["kind"],
                    "status": row["status"],
                    "stats": stats,
                })
        return runs

    def get_audit_logs(self, run_id: Optional[str] = None, agente: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera entradas del registro de auditoría."""
        logs: List[Dict[str, Any]] = []
        query = "SELECT * FROM audit_log"
        params: List[Any] = []
        clauses = []
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if agente:
            clauses.append("agente = ?")
            params.append(agente)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            for row in cur.fetchall():
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except json.JSONDecodeError:
                    payload = {}
                logs.append({
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "agente": row["agente"],
                    "accion": row["accion"],
                    "payload": payload,
                    "ts": row["ts"],
                })
        return logs

    def save_narrative(self, narrative_data: Dict[str, Any], items: Optional[List[Dict[str, Any]]] = None) -> None:
        """Almacena o actualiza el estado evolutivo de una narrativa temporal."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO narratives
                (id, nombre, first_seen, last_seen, fase, novelty, recurrencia, pico_fecha, semanas_desde_pico, ratio_copias, fuentes_distintas, sparkline, actualizado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    narrative_data["id"],
                    narrative_data["nombre"],
                    narrative_data.get("first_seen"),
                    narrative_data.get("last_seen"),
                    narrative_data.get("fase", "emergente"),
                    narrative_data.get("novelty", 1.0),
                    narrative_data.get("recurrencia", 1),
                    narrative_data.get("pico_fecha"),
                    narrative_data.get("semanas_desde_pico", 0),
                    narrative_data.get("ratio_copias", 0.0),
                    narrative_data.get("fuentes_distintas", 1),
                    narrative_data.get("sparkline", ""),
                    now,
                ),
            )
            if items:
                for it in items:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO narrative_items (narrative_id, item_id, similitud)
                        VALUES (?, ?, ?)
                        """,
                        (narrative_data["id"], it["item_id"], it.get("similitud", 1.0)),
                    )
            conn.commit()

    def get_narratives(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera narrativas rastreadas por el Agente Historiador."""
        narratives: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM narratives ORDER BY actualizado_en DESC LIMIT ?", (limit,))
            for row in cur.fetchall():
                narratives.append(dict(row))
        return narratives

    def save_verdict(self, verdict_data: Dict[str, Any]) -> None:
        """Guarda la auditoría del Agente Crítico para una narrativa."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO verdicts
                (narrative_id, veracidad_p, impacto_real, humo_p, veredicto, razones_json, evaluado_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verdict_data["narrative_id"],
                    verdict_data.get("veracidad_p", 0.5),
                    verdict_data.get("impacto_real", 0.5),
                    verdict_data.get("humo_p", 0.0),
                    verdict_data.get("veredicto", "valido"),
                    json.dumps(verdict_data.get("razones", []), ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()

    def get_verdict(self, narrative_id: str) -> Optional[Dict[str, Any]]:
        """Recupera el veredicto del Agente Crítico para una narrativa."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM verdicts WHERE narrative_id = ?", (narrative_id,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                try:
                    d["razones"] = json.loads(d.get("razones_json") or "[]")
                except json.JSONDecodeError:
                    d["razones"] = []
                return d
        return None

    def save_item_embedding(self, item_id: str, vector_blob: bytes, dim: int) -> None:
        """Guarda el vector embedding para un ítem en SQLite."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO item_embeddings (item_id, vector_blob, dim)
                VALUES (?, ?, ?)
                """,
                (item_id, vector_blob, dim),
            )
            conn.commit()

    def get_all_item_embeddings(self) -> List[Tuple[str, bytes, int]]:
        """Recupera todos los embeddings indexados."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT item_id, vector_blob, dim FROM item_embeddings")
            return [(r["item_id"], r["vector_blob"], r["dim"]) for r in cur.fetchall()]

    # =========================================================================
    # MÉTODOS DEL CHATBOT RAG (TARJETAS DE NARRATIVA, CACHÉ Y OBSERVABILIDAD)
    # =========================================================================

    def save_narrative_card(self, narrative_id: str, texto: str, embedding: Optional[bytes] = None) -> None:
        """Guarda o actualiza una tarjeta de narrativa materializada para RAG."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO narrative_cards (narrative_id, texto, embedding, actualizado_at)
                VALUES (?, ?, ?, ?)
                """,
                (narrative_id, texto, embedding, now),
            )
            conn.commit()

    def get_narrative_card(self, narrative_id: str) -> Optional[Dict[str, Any]]:
        """Recupera la tarjeta de narrativa por su identificador."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM narrative_cards WHERE narrative_id = ?", (narrative_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_narrative_cards(self) -> List[Dict[str, Any]]:
        """Recupera todas las tarjetas de narrativa materializadas."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM narrative_cards ORDER BY actualizado_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def save_chat_log(self, log_data: Dict[str, Any]) -> None:
        """Registra un evento de consulta del chatbot en chat_logs para observabilidad."""
        now = datetime.now(timezone.utc).isoformat()
        log_id = log_data.get("id") or f"chat_{int(time.time()*1000)}"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO chat_logs (
                    id, pregunta, intencion, nivel, modelo, latencia_ms,
                    escalado, razon_escalado, tokens, coste_usd, groundedness, ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    log_data.get("pregunta", ""),
                    log_data.get("intencion"),
                    log_data.get("nivel", "T0"),
                    log_data.get("modelo", "deterministic"),
                    log_data.get("latencia_ms", 0.0),
                    1 if log_data.get("escalado") else 0,
                    log_data.get("razon_escalado"),
                    log_data.get("tokens", 0),
                    log_data.get("coste_usd", 0.0),
                    log_data.get("groundedness"),
                    now,
                ),
            )
            conn.commit()

    def get_chat_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera el historial reciente de consultas del chatbot."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM chat_logs ORDER BY ts DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_cached_answer(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Obtiene una respuesta cacheada válida (no invalidada)."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM answers_cache WHERE hash = ? AND invalidado_at IS NULL",
                (query_hash,),
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                try:
                    d["respuesta"] = json.loads(d["respuesta_json"])
                except Exception:
                    d["respuesta"] = d["respuesta_json"]
                return d
        return None

    def cache_answer(self, query_hash: str, pregunta: str, respuesta_data: Dict[str, Any], nivel: str) -> None:
        """Almacena en caché una respuesta de consulta."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO answers_cache (hash, pregunta, respuesta_json, nivel, creado_at, invalidado_at)
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (query_hash, pregunta, json.dumps(respuesta_data, ensure_ascii=False), nivel, now),
            )
            conn.commit()

    def invalidate_answers_cache(self) -> int:
        """Invalida todas las entradas de caché activas (usado al terminar cada ciclo del radar)."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE answers_cache SET invalidado_at = ? WHERE invalidado_at IS NULL", (now,))
            conn.commit()
            return cur.rowcount

    # =========================================================================
    # MÉTODOS DEL GESTOR DE BORRADORES (DRAFTS & VERSIONES)
    # =========================================================================

    def save_draft_record(self, draft_data: Dict[str, Any]) -> int:
        """Guarda o actualiza un registro de borrador en SQLite. Retorna el ID del borrador."""
        now = datetime.now(timezone.utc).isoformat()
        draft_id = draft_data.get("id")
        created_at = draft_data.get("created_at") or now
        updated_at = draft_data.get("updated_at") or now
        metricas = json.dumps(draft_data.get("metricas_json") or {}, ensure_ascii=False)

        with self.get_connection() as conn:
            cur = conn.cursor()
            if draft_id is not None:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO drafts (
                        id, narrative_id, titulo, formato, gancho, estado,
                        autor, created_at, updated_at, published_url, metricas_json, path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id,
                        draft_data.get("narrative_id"),
                        draft_data["titulo"],
                        draft_data.get("formato", "video_corto"),
                        draft_data.get("gancho", "opinion"),
                        draft_data.get("estado", "borrador"),
                        draft_data.get("autor", "30X Media"),
                        created_at,
                        updated_at,
                        draft_data.get("published_url"),
                        metricas,
                        draft_data.get("path", ""),
                    ),
                )
                conn.commit()
                return draft_id
            else:
                cur.execute(
                    """
                    INSERT INTO drafts (
                        narrative_id, titulo, formato, gancho, estado,
                        autor, created_at, updated_at, published_url, metricas_json, path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_data.get("narrative_id"),
                        draft_data["titulo"],
                        draft_data.get("formato", "video_corto"),
                        draft_data.get("gancho", "opinion"),
                        draft_data.get("estado", "borrador"),
                        draft_data.get("autor", "30X Media"),
                        created_at,
                        updated_at,
                        draft_data.get("published_url"),
                        metricas,
                        draft_data.get("path", ""),
                    ),
                )
                conn.commit()
                return cur.lastrowid

    def get_draft_record(self, draft_id: int) -> Optional[Dict[str, Any]]:
        """Recupera un borrador por su ID numérico."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                try:
                    d["metricas_json"] = json.loads(d.get("metricas_json") or "{}")
                except json.JSONDecodeError:
                    d["metricas_json"] = {}
                return d
        return None

    def list_draft_records(self, estado: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista borradores, opcionalmente filtrados por estado."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            if estado:
                cur.execute("SELECT * FROM drafts WHERE estado = ? ORDER BY id DESC", (estado,))
            else:
                cur.execute("SELECT * FROM drafts ORDER BY id DESC")
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["metricas_json"] = json.loads(d.get("metricas_json") or "{}")
                except json.JSONDecodeError:
                    d["metricas_json"] = {}
                result.append(d)
            return result

    def update_draft_status(self, draft_id: int, nuevo_estado: str) -> bool:
        """Actualiza el estado de un borrador en SQLite."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE drafts SET estado = ?, updated_at = ? WHERE id = ?",
                (nuevo_estado, now, draft_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def add_draft_version(self, draft_id: int, version: int, contenido: str, autor: str = "30X Media") -> None:
        """Añade una versión snapshot de un borrador."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO draft_versions (draft_id, version, contenido, autor, ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (draft_id, version, contenido, autor, now),
            )
            conn.commit()

    def get_draft_versions(self, draft_id: int) -> List[Dict[str, Any]]:
        """Recupera el historial de versiones de un borrador."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM draft_versions WHERE draft_id = ? ORDER BY version ASC",
                (draft_id,),
            )
            return [dict(r) for r in cur.fetchall()]
