"""Gestor de Borradores de Contenido para Radar30X.

Convierte narrativas detectadas por el radar en piezas editoriales en formato Markdown,
con control de versiones Git, transiciones de estado estrictas e índice relacional en SQLite.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from pipeline.db import Database

logger = logging.getLogger(__name__)

# Máquina de estados con transiciones estrictas (§10)
VALID_TRANSITIONS = {
    "idea": {"borrador", "descartado"},
    "borrador": {"en_revision", "descartado"},
    "en_revision": {"borrador", "aprobado", "descartado"},
    "aprobado": {"publicado", "borrador"},
    "publicado": set(),
    "descartado": {"borrador"},  # Permite rescate deliberado
}


def slugify(text: str) -> str:
    """Convierte un título en un slug legible para nombre de archivo."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "borrador"


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extrae el front-matter YAML simple y el cuerpo markdown."""
    frontmatter: Dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].lstrip("\r\n")

            current_key = None
            current_list: Optional[List[str]] = None

            for line in fm_text.splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue

                if line_str.startswith("- ") and current_list is not None:
                    current_list.append(line_str[2:].strip().strip('"').strip("'"))
                    continue

                if ":" in line_str:
                    k, v = line_str.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if not v:
                        current_key = k
                        current_list = []
                        frontmatter[k] = current_list
                    else:
                        current_key = None
                        current_list = None
                        if v.isdigit():
                            frontmatter[k] = int(v)
                        else:
                            frontmatter[k] = v

    return frontmatter, body


def serialize_frontmatter(fm: Dict[str, Any], body: str) -> str:
    """Serializa diccionario de front-matter y cuerpo en formato Markdown limpio."""
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    lines.append(body.strip() + "\n")
    return "\n".join(lines)


class DraftManager:
    """Administrador de ciclo de vida de borradores."""

    def __init__(self, db: Optional[Database] = None, base_dir: Optional[str] = None) -> None:
        self.db = db or Database()
        self.base_dir = Path(base_dir or (Path(__file__).resolve().parent.parent / "drafts"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_draft(
        self,
        narrative_id: Optional[str] = None,
        titulo: Optional[str] = None,
        formato: str = "video_corto",
        gancho: str = "opinion",
        autor: str = "30X Media",
        evidencia: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Crea un nuevo borrador a partir de una narrativa o tema libre."""
        now = datetime.now(timezone.utc)
        semana = now.strftime("%Y-W%W")
        semana_dir = self.base_dir / semana
        semana_dir.mkdir(parents=True, exist_ok=True)

        evidencia = evidencia or []

        # Si viene de una narrativa, extraer datos reales si existen
        narrative_context = {}
        if narrative_id:
            report = self.db.get_latest_report()
            top_temas = report.get("top_temas", []) if report else []
            for t in top_temas:
                t_id = t.get("narrative_id") or str(t.get("posicion"))
                if t_id == str(narrative_id) or str(t.get("posicion")) == str(narrative_id):
                    titulo = titulo or t.get("tema")
                    formato = t.get("formato") or formato
                    gancho = t.get("gancho") or gancho
                    evidencia = t.get("evidencia") or evidencia
                    narrative_context = {
                        "por_que": t.get("por_que", ""),
                        "por_que_audiencia": t.get("por_que_audiencia", ""),
                        "adaptacion_30x": t.get("adaptacion_30x", ""),
                        "fase": t.get("fase", "Crecimiento"),
                        "score": t.get("score", 0),
                        "veredicto_critico": t.get("veredicto_critico", {}),
                    }
                    break

        titulo = titulo or f"Nueva pieza editorial {now.strftime('%d/%m')}"
        slug = slugify(titulo)
        filename = f"{slug}.md"
        file_path = semana_dir / filename

        # Evitar colisión de nombres
        counter = 1
        while file_path.exists():
            file_path = semana_dir / f"{slug}-{counter}.md"
            counter += 1

        # Registrar primero en SQLite para obtener el draft_id
        draft_record = {
            "narrative_id": narrative_id,
            "titulo": titulo,
            "formato": formato,
            "gancho": gancho,
            "estado": "borrador",
            "autor": autor,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "path": str(file_path),
        }
        draft_id = self.db.save_draft_record(draft_record)

        # Construir contenido inicial del borrador pasando por LLM
        frontmatter = {
            "draft_id": draft_id,
            "narrative_id": narrative_id or "libre",
            "titulo": titulo,
            "estado": "borrador",
            "formato": formato,
            "gancho": gancho,
            "autor": autor,
            "creado": now.strftime("%Y-%m-%d"),
            "actualizado": now.strftime("%Y-%m-%d"),
            "evidencia": evidencia,
        }

        from drafts.generator import generate_draft_body_llm
        body = generate_draft_body_llm(
            titulo=titulo,
            formato=formato,
            gancho=gancho,
            evidencia=evidencia,
            narrative_context=narrative_context,
            autor=autor,
        )

        file_content = serialize_frontmatter(frontmatter, body)
        try:
            file_path.write_text(file_content, encoding="utf-8")
        except OSError as oe:
            logger.warning("No se pudo escribir archivo físico de borrador (%s). Persistido en SQLite.", oe)

        # Registrar versión 1
        self.db.add_draft_version(draft_id=draft_id, version=1, contenido=file_content, autor=autor)

        # Auto-commit git si aplica
        if file_path.exists():
            self._git_commit(file_path, f"draft({draft_id}): nuevo borrador '{titulo}'")

        return {
            "id": draft_id,
            "titulo": titulo,
            "formato": formato,
            "gancho": gancho,
            "estado": "borrador",
            "version": 1,
            "path": str(file_path),
            "body": body,
            "content": file_content,
        }

    def update_status(self, draft_id: int, nuevo_estado: str) -> Dict[str, Any]:
        """Transiciona el estado de un borrador validando las reglas de la máquina de estados."""
        nuevo_estado = nuevo_estado.lower().strip()
        record = self.db.get_draft_record(draft_id)
        if not record:
            raise ValueError(f"No existe el borrador con ID {draft_id}.")

        estado_actual = record["estado"]
        permitidos = VALID_TRANSITIONS.get(estado_actual, set())

        if nuevo_estado not in permitidos and nuevo_estado != estado_actual:
            raise ValueError(
                f"Transición inválida: de '{estado_actual}' no se puede pasar a '{nuevo_estado}'. "
                f"Estados permitidos: {sorted(list(permitidos))}."
            )

        file_path = Path(record["path"])
        now = datetime.now(timezone.utc)

        # Actualizar archivo Markdown si existe
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)
            fm["estado"] = nuevo_estado
            fm["actualizado"] = now.strftime("%Y-%m-%d")
            updated_content = serialize_frontmatter(fm, body)
            file_path.write_text(updated_content, encoding="utf-8")

            # Guardar nueva versión
            versions = self.db.get_draft_versions(draft_id)
            next_ver = len(versions) + 1
            self.db.add_draft_version(
                draft_id=draft_id,
                version=next_ver,
                contenido=updated_content,
                autor=record.get("autor", "30X Media"),
            )

            # Git auto-commit
            self._git_commit(file_path, f"draft({draft_id}): {estado_actual} -> {nuevo_estado}")

        # Actualizar base de datos
        self.db.update_draft_status(draft_id, nuevo_estado)
        return {
            "id": draft_id,
            "estado_anterior": estado_actual,
            "nuevo_estado": nuevo_estado,
            "path": str(file_path),
        }

    def update_draft_content(
        self,
        draft_id: int,
        new_body: str,
        new_title: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Actualiza el contenido markdown de un borrador existente, persistiendo la nueva versión."""
        record = self.db.get_draft_record(draft_id)
        if not record:
            raise ValueError(f"No existe borrador con ID {draft_id}")

        file_path = Path(record["path"])
        frontmatter: Dict[str, Any] = {}
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)

        if new_title:
            frontmatter["titulo"] = new_title

        frontmatter["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated_content = serialize_frontmatter(frontmatter, new_body)

        file_path.write_text(updated_content, encoding="utf-8")

        versions = self.db.get_draft_versions(draft_id)
        next_ver = len(versions) + 1
        self.db.add_draft_version(
            draft_id=draft_id,
            version=next_ver,
            contenido=updated_content,
            autor=author or record.get("autor", "30X Media"),
        )
        self._git_commit(file_path, f"draft({draft_id}): edit content v{next_ver}")

        updated_draft = self.get_draft(draft_id)
        return updated_draft or {"id": draft_id, "body": new_body, "version": next_ver}

    def list_drafts(self, estado: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todos los borradores registrados en el sistema enriquecidos con su contenido."""
        records = self.db.list_draft_records(estado=estado)
        enriched: List[Dict[str, Any]] = []
        for r in records:
            d = self.get_draft(r["id"])
            if d:
                enriched.append(d)
            else:
                enriched.append(r)
        return enriched

    def get_draft(self, draft_id: int) -> Optional[Dict[str, Any]]:
        """Recupera la información y contenido completo de un borrador."""
        record = self.db.get_draft_record(draft_id)
        if not record:
            return None

        file_path = Path(record["path"])
        versions = self.db.get_draft_versions(draft_id)
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)
            record["content"] = content
            record["frontmatter"] = fm
            record["body"] = body
        elif versions:
            content = versions[-1].get("contenido", "")
            fm, body = parse_frontmatter(content)
            record["content"] = content
            record["frontmatter"] = fm
            record["body"] = body
        else:
            record["content"] = ""
            record["frontmatter"] = {}
            record["body"] = ""

        record["versions"] = versions
        return record

    def get_diff(self, draft_id: int) -> str:
        """Obtiene el diff de Git o entre versiones para el archivo del borrador."""
        record = self.db.get_draft_record(draft_id)
        if not record:
            return f"Borrador #{draft_id} no encontrado."

        file_path = record["path"]
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD~1", "--", file_path],
                capture_output=True,
                text=True,
                cwd=str(self.base_dir.parent),
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout
        except Exception:
            pass

        # Fallback a comparación entre versiones en SQLite
        versions = self.db.get_draft_versions(draft_id)
        if len(versions) >= 2:
            v_ant = versions[-2]["contenido"]
            v_act = versions[-1]["contenido"]
            import difflib

            diff_lines = list(
                difflib.unified_diff(
                    v_ant.splitlines(),
                    v_act.splitlines(),
                    fromfile=f"v{versions[-2]['version']}",
                    tofile=f"v{versions[-1]['version']}",
                    lineterm="",
                )
            )
            return "\n".join(diff_lines) if diff_lines else "Sin cambios entre versiones recientes."

        return "No hay suficientes versiones previas para generar un diff."

    def _git_commit(self, file_path: Path, commit_msg: str) -> None:
        """Realiza auto-commit en git con manejo seguro de fallos."""
        try:
            repo_root = self.base_dir.parent
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=str(repo_root),
                capture_output=True,
                timeout=5,
                check=False,
            )
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(repo_root),
                capture_output=True,
                timeout=5,
                check=False,
            )
        except Exception as ex:
            logger.debug("Auto-commit de git omitido o fallido: %s", ex)
