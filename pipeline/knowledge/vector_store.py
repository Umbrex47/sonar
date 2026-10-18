"""Almacén Vectorial embebido en SQLite para la Base de Conocimiento de Radar30X.

Permite indexar y buscar fragmentos semánticos y perfiles de estilo con similitud de coseno
directamente en SQLite (radar.db), sin necesidad de servicios externos ni Docker.
"""

from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
import struct
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

from pipeline.knowledge.models import (
    HookAnalysis,
    KnowledgeChunk,
    KnowledgeProfile,
    KnowledgeSource,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/radar.db"


def _get_db_path(custom_path: Optional[str] = None) -> str:
    if custom_path:
        return custom_path
    if "RADAR_DB_PATH" in os.environ:
        return os.environ["RADAR_DB_PATH"]
    base_dir = Path(__file__).resolve().parent.parent.parent
    return str(base_dir / DEFAULT_DB_PATH)


class VectorStore:
    """Motor de almacenamiento y búsqueda vectorial integrado en SQLite."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = _get_db_path(db_path)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.init_tables()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self) -> None:
        """Crea las tablas de conocimiento vectorial si no existen y aplica migraciones seguras."""
        with self.get_connection() as conn:
            cur = conn.cursor()

            # 1. Fuentes de conocimiento
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    id TEXT PRIMARY KEY,
                    tipo TEXT NOT NULL,
                    modo_extraccion TEXT DEFAULT 'completo',
                    url_o_path TEXT NOT NULL,
                    imagen_preview TEXT,
                    imagenes_pool_json TEXT,
                    total_imagenes INTEGER DEFAULT 1,
                    titulo TEXT NOT NULL,
                    autor TEXT,
                    duracion_segundos REAL DEFAULT 0.0,
                    solicitud_usuario TEXT NOT NULL,
                    transcripcion_resumen TEXT,
                    creado_en TEXT NOT NULL
                )
            """
            )

            # 2. Perfiles de estilo, ganchos y palabras clave
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_profiles (
                    source_id TEXT PRIMARY KEY,
                    modo_extraccion TEXT DEFAULT 'completo',
                    hook_json TEXT,
                    estructura_json TEXT,
                    tono_y_voz TEXT,
                    conceptos_json TEXT,
                    palabras_clave_json TEXT,
                    palabras_secundarias_json TEXT,
                    entidades_json TEXT,
                    enfoques_radar_json TEXT,
                    texto_extraido TEXT,
                    plantillas_json TEXT,
                    resumen_ejecutivo TEXT,
                    FOREIGN KEY(source_id) REFERENCES knowledge_sources(id)
                )
            """
            )

            # 3. Chunks semánticos con vectores en BLOB
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    timestamp_inicio REAL DEFAULT 0.0,
                    timestamp_fin REAL DEFAULT 0.0,
                    texto TEXT NOT NULL,
                    tags_json TEXT,
                    embedding_blob BLOB,
                    metadata_json TEXT,
                    FOREIGN KEY(source_id) REFERENCES knowledge_sources(id)
                )
            """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON knowledge_chunks(source_id)")

            # Migraciones no destructivas para bases de datos existentes
            migrations = [
                ("knowledge_sources", "modo_extraccion TEXT DEFAULT 'completo'"),
                ("knowledge_sources", "imagen_preview TEXT"),
                ("knowledge_sources", "imagenes_pool_json TEXT"),
                ("knowledge_sources", "total_imagenes INTEGER DEFAULT 1"),
                ("knowledge_profiles", "modo_extraccion TEXT DEFAULT 'completo'"),
                ("knowledge_profiles", "palabras_clave_json TEXT"),
                ("knowledge_profiles", "palabras_secundarias_json TEXT"),
                ("knowledge_profiles", "entidades_json TEXT"),
                ("knowledge_profiles", "enfoques_radar_json TEXT"),
                ("knowledge_profiles", "texto_extraido TEXT"),
            ]
            for table, col_def in migrations:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                except sqlite3.OperationalError:
                    pass  # Columna ya existe

            conn.commit()

    @staticmethod
    def pack_embedding(vec: List[float]) -> bytes:
        """Empaqueta una lista de float32 a un buffer binario eficiente."""
        return struct.pack(f"{len(vec)}f", *vec)

    @staticmethod
    def unpack_embedding(blob: bytes) -> List[float]:
        """Desempaqueta un buffer binario a una lista de floats."""
        count = len(blob) // 4
        return list(struct.unpack(f"{count}f", blob))

    def generate_embedding(self, text: str) -> List[float]:
        """Genera un vector semántico para el texto.
        
        Usa OpenAI text-embedding-3-small si la API key está presente,
        o un generador semántico determinista de 256 dimensiones como fallback local.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and not api_key.startswith("sk-placeholder"):
            try:
                base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                with httpx.Client(timeout=10.0, trust_env=False) as client:
                    resp = client.post(
                        f"{base_url}/embeddings",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={"input": text[:8000], "model": "text-embedding-3-small"},
                    )
                    if resp.status_code == 200:
                        return resp.json()["data"][0]["embedding"]
            except Exception as e:
                logger.warning("Fallo al llamar API de embeddings: %s. Usando fallback local.", e)

        # Fallback local determinista y calibrado (256 dimensiones normalizadas)
        import hashlib
        dim = 256
        vec = [0.0] * dim
        words = text.lower().split()
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            val = ((h >> 8) % 1000) / 1000.0 - 0.5
            vec[idx] += val
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 5) for x in vec]

    def save_source_and_profile(
        self,
        source: KnowledgeSource,
        profile: KnowledgeProfile,
        chunks: List[KnowledgeChunk],
    ) -> None:
        """Guarda la fuente, el perfil de gancho y todos los chunks vectoriales asociados."""
        with self.get_connection() as conn:
            cur = conn.cursor()

            # Insertar fuente
            imagenes_pool_data = json.dumps(source.imagenes_pool, ensure_ascii=False) if source.imagenes_pool else "[]"
            cur.execute(
                """
                INSERT OR REPLACE INTO knowledge_sources
                (id, tipo, modo_extraccion, url_o_path, imagen_preview, imagenes_pool_json, total_imagenes, titulo, autor, duracion_segundos, solicitud_usuario, transcripcion_resumen, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.tipo,
                    source.modo_extraccion,
                    source.url_o_path,
                    source.imagen_preview,
                    imagenes_pool_data,
                    source.total_imagenes,
                    source.titulo,
                    source.autor,
                    source.duracion_segundos,
                    source.solicitud_usuario,
                    source.transcripcion_resumen,
                    source.creado_en,
                ),
            )

            # Insertar perfil
            hook_data = json.dumps(profile.hook.model_dump(), ensure_ascii=False) if profile.hook else "{}"
            cur.execute(
                """
                INSERT OR REPLACE INTO knowledge_profiles
                (source_id, modo_extraccion, hook_json, estructura_json, tono_y_voz, conceptos_json,
                 palabras_clave_json, palabras_secundarias_json, entidades_json, enfoques_radar_json,
                 texto_extraido, plantillas_json, resumen_ejecutivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.source_id,
                    profile.modo_extraccion,
                    hook_data,
                    json.dumps(profile.estructura_narrativa, ensure_ascii=False),
                    profile.tono_y_voz,
                    json.dumps(profile.conceptos_clave, ensure_ascii=False),
                    json.dumps(profile.palabras_clave, ensure_ascii=False),
                    json.dumps(profile.palabras_clave_secundarias, ensure_ascii=False),
                    json.dumps(profile.entidades_detectadas, ensure_ascii=False),
                    json.dumps(profile.enfoques_radar_sugeridos, ensure_ascii=False),
                    profile.texto_extraido,
                    json.dumps(profile.plantillas_30x, ensure_ascii=False),
                    profile.resumen_ejecutivo,
                ),
            )

            # Insertar chunks
            for ch in chunks:
                emb_bytes = self.pack_embedding(ch.embedding) if ch.embedding else None
                cur.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_chunks
                    (id, source_id, chunk_index, timestamp_inicio, timestamp_fin, texto, tags_json, embedding_blob, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ch.id,
                        ch.source_id,
                        ch.chunk_index,
                        ch.timestamp_inicio,
                        ch.timestamp_fin,
                        ch.texto,
                        json.dumps(ch.tags, ensure_ascii=False),
                        emb_bytes,
                        json.dumps(ch.metadata_extra, ensure_ascii=False),
                    ),
                )
            conn.commit()
        logger.info("Guardada fuente '%s' (%s) con %d chunks vectoriales.", source.titulo, source.modo_extraccion, len(chunks))

    def get_all_sources(self) -> List[KnowledgeSource]:
        """Obtiene todas las fuentes registradas junto con su perfil de estilo y palabras clave."""
        sources: List[KnowledgeSource] = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.*,
                       p.modo_extraccion AS p_modo,
                       p.hook_json,
                       p.estructura_json,
                       p.tono_y_voz,
                       p.conceptos_json,
                       p.palabras_clave_json,
                       p.palabras_secundarias_json,
                       p.entidades_json,
                       p.enfoques_radar_json,
                       p.texto_extraido,
                       p.plantillas_json,
                       p.resumen_ejecutivo
                FROM knowledge_sources s
                LEFT JOIN knowledge_profiles p ON s.id = p.source_id
                ORDER BY s.creado_en DESC
                """
            )
            for row in cur.fetchall():
                profile = None
                keys = row.keys()
                has_profile = "p_modo" in keys and (
                    row["p_modo"] is not None
                    or row["hook_json"] is not None
                    or row["conceptos_json"] is not None
                    or (("palabras_clave_json" in keys) and row["palabras_clave_json"] is not None)
                )

                if has_profile:
                    hook_obj = None
                    if row["hook_json"]:
                        try:
                            hook_data = json.loads(row["hook_json"])
                            if hook_data:
                                hook_obj = HookAnalysis(**hook_data)
                        except Exception as ex:
                            logger.warning("Error deserializando hook para %s: %s", row["id"], ex)

                    def _safe_json_list(col_name: str) -> List[Any]:
                        if col_name in keys and row[col_name]:
                            try:
                                return json.loads(row[col_name])
                            except Exception:
                                return []
                        return []

                    profile = KnowledgeProfile(
                        source_id=row["id"],
                        modo_extraccion=row["p_modo"] or (row["modo_extraccion"] if "modo_extraccion" in keys else "completo") or "completo",
                        hook=hook_obj,
                        estructura_narrativa=_safe_json_list("estructura_json"),
                        tono_y_voz=row["tono_y_voz"] or "",
                        conceptos_clave=_safe_json_list("conceptos_json"),
                        palabras_clave=_safe_json_list("palabras_clave_json"),
                        palabras_clave_secundarias=_safe_json_list("palabras_secundarias_json"),
                        entidades_detectadas=_safe_json_list("entidades_json"),
                        enfoques_radar_sugeridos=_safe_json_list("enfoques_radar_json"),
                        texto_extraido=row["texto_extraido"] if "texto_extraido" in keys else None,
                        plantillas_30x=_safe_json_list("plantillas_json"),
                        resumen_ejecutivo=row["resumen_ejecutivo"] or "",
                    )

                pool_list = _safe_json_list("imagenes_pool_json")
                tot_img = (
                    row["total_imagenes"]
                    if ("total_imagenes" in keys and row["total_imagenes"])
                    else (len(pool_list) if pool_list else 1)
                )

                sources.append(
                    KnowledgeSource(
                        id=row["id"],
                        tipo=row["tipo"],
                        modo_extraccion=row["modo_extraccion"] if "modo_extraccion" in keys and row["modo_extraccion"] else "completo",
                        url_o_path=row["url_o_path"],
                        imagen_preview=row["imagen_preview"] if "imagen_preview" in keys else None,
                        imagenes_pool=pool_list,
                        total_imagenes=tot_img,
                        titulo=row["titulo"],
                        autor=row["autor"] or "Desconocido",
                        duracion_segundos=row["duracion_segundos"] or 0.0,
                        solicitud_usuario=row["solicitud_usuario"],
                        transcripcion_resumen=row["transcripcion_resumen"] or "",
                        creado_en=row["creado_en"],
                        perfil=profile,
                    )
                )
        return sources

    def get_source_by_id(self, source_id: str) -> Optional[Tuple[KnowledgeSource, List[KnowledgeChunk]]]:
        """Recupera la fuente y todos sus chunks ordenados por timestamp."""
        all_sources = [s for s in self.get_all_sources() if s.id == source_id]
        if not all_sources:
            return None
        source = all_sources[0]

        chunks: List[KnowledgeChunk] = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM knowledge_chunks WHERE source_id = ? ORDER BY chunk_index ASC",
                (source_id,),
            )
            for r in cur.fetchall():
                emb = self.unpack_embedding(r["embedding_blob"]) if r["embedding_blob"] else []
                chunks.append(
                    KnowledgeChunk(
                        id=r["id"],
                        source_id=r["source_id"],
                        chunk_index=r["chunk_index"],
                        timestamp_inicio=r["timestamp_inicio"],
                        timestamp_fin=r["timestamp_fin"],
                        texto=r["texto"],
                        tags=json.loads(r["tags_json"] or "[]"),
                        embedding=emb,
                        metadata_extra=json.loads(r["metadata_json"] or "{}"),
                    )
                )
        return source, chunks

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        tag_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Realiza búsqueda semántica por similitud de coseno en los chunks vectoriales."""
        query_vec = np.array(self.generate_embedding(query), dtype=np.float32)
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return []

        results: List[Tuple[float, Dict[str, Any]]] = []

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT c.*, s.titulo AS source_titulo, s.url_o_path, s.solicitud_usuario, s.autor
                FROM knowledge_chunks c
                JOIN knowledge_sources s ON c.source_id = s.id
                """
            )
            for r in cur.fetchall():
                blob = r["embedding_blob"]
                if not blob:
                    continue
                cand_vec = np.frombuffer(blob, dtype=np.float32)
                if len(cand_vec) != len(query_vec):
                    continue

                c_norm = np.linalg.norm(cand_vec)
                if c_norm == 0:
                    continue

                score = float(np.dot(query_vec, cand_vec) / (q_norm * c_norm))

                # Filtro opcional por tag
                tags = json.loads(r["tags_json"] or "[]")
                if tag_filter and tag_filter.lower() not in [t.lower() for t in tags]:
                    continue

                results.append((
                    score,
                    {
                        "chunk_id": r["id"],
                        "source_id": r["source_id"],
                        "source_titulo": r["source_titulo"],
                        "url_o_path": r["url_o_path"],
                        "autor": r["autor"],
                        "solicitud_usuario": r["solicitud_usuario"],
                        "timestamp_inicio": r["timestamp_inicio"],
                        "timestamp_fin": r["timestamp_fin"],
                        "texto": r["texto"],
                        "tags": tags,
                        "score": round(score, 4),
                    },
                ))

        # Ordenar de mayor a menor similitud
        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:top_k]]

    def delete_source(self, source_id: str) -> bool:
        """Elimina una fuente, su perfil y sus chunks asociados."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_chunks WHERE source_id = ?", (source_id,))
            cur.execute("DELETE FROM knowledge_profiles WHERE source_id = ?", (source_id,))
            cur.execute("DELETE FROM knowledge_sources WHERE id = ?", (source_id,))
            conn.commit()
            return cur.rowcount > 0
