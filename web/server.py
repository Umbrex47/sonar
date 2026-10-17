"""Servidor HTTP nativo y ligero para la interfaz web de Radar30X.

No requiere frameworks pesados adicionales; utiliza la librería estándar de Python
(http.server.ThreadingHTTPServer) para responder con latencia ultrabaja (< 5ms)
y servir la API de reportes, enriquecimiento de evidencias y ejecución en segundo plano.
"""

from datetime import datetime, timezone
import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("radar30x.web")

# Estado global de ejecución del pipeline
RUN_STATE = {
    "is_running": False,
    "last_run": None,
    "last_status": "idle",
    "last_error": None,
}
RUN_LOCK = threading.Lock()


def get_base_dir() -> Path:
    """Retorna el directorio raíz del proyecto radar30x."""
    return Path(__file__).resolve().parent.parent


def get_db_path() -> str:
    """Retorna la ruta a la base de datos SQLite."""
    return str(get_base_dir() / "data" / "radar.db")


def get_out_dir() -> Path:
    """Retorna el directorio de reportes out/."""
    return get_base_dir() / "out"


def enrich_report_references(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquece las URLs de evidencia con datos detallados (título, fuente, autor, métricas) desde SQLite."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return report_data

    # Mapear URLs a datos del ítem
    items_by_url: Dict[str, Dict[str, Any]] = {}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT fuente, titulo, url, autor, fecha, metricas_json FROM items")
        for row in cur.fetchall():
            url = row["url"]
            try:
                metricas = json.loads(row["metricas_json"] or "{}")
            except Exception:
                metricas = {}
            items_by_url[url] = {
                "fuente": row["fuente"],
                "titulo": row["titulo"],
                "autor": row["autor"] or "Redacción / Autor",
                "fecha": row["fecha"] or "",
                "metricas": metricas,
                "url": url,
            }
        conn.close()
    except Exception as e:
        logger.warning("No se pudo conectar a SQLite para enriquecer evidencias: %s", e)
        return report_data

    # Clonar reporte para enriquecer
    enriched = dict(report_data)
    top_temas = enriched.get("top_temas", [])
    new_top = []

    for t in top_temas:
        tema_copy = dict(t)
        raw_evidencia = tema_copy.get("evidencia", [])
        referencias_detalladas = []

        for url in raw_evidencia:
            if url in items_by_url:
                referencias_detalladas.append(items_by_url[url])
            else:
                # Extraer dominio amigable como fallback
                domain = urlparse(url).netloc.replace("www.", "") or "Fuente externa"
                path_slug = urlparse(url).path.strip("/").split("/")[-1].replace("-", " ").title()
                titulo_fb = path_slug if path_slug else domain
                referencias_detalladas.append({
                    "fuente": domain.split(".")[0].capitalize(),
                    "titulo": titulo_fb,
                    "autor": domain,
                    "fecha": "Reciente",
                    "metricas": {},
                    "url": url,
                })

        tema_copy["referencias_detalladas"] = referencias_detalladas
        new_top.append(tema_copy)

    enriched["top_temas"] = new_top
    return enriched


def get_report_files() -> List[str]:
    """Retorna los archivos de reporte ordenados por fecha de modificación descendente, priorizando reportes reales."""
    out_dir = get_out_dir()
    all_files = glob.glob(str(out_dir / "report_*.json"))
    real_files = [f for f in all_files if not f.endswith("report_sample.json")]
    if real_files:
        return sorted(real_files, key=os.path.getmtime, reverse=True)
    return sorted(all_files, key=os.path.getmtime, reverse=True)


def load_latest_report() -> Optional[Dict[str, Any]]:
    """Carga el reporte JSON más reciente del directorio out/."""
    report_files = get_report_files()
    if not report_files:
        return None

    try:
        with open(report_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        return enrich_report_references(data)
    except Exception as e:
        logger.error("Error al cargar reporte más reciente: %s", e)
        return None


def load_report_by_name(filename: str) -> Optional[Dict[str, Any]]:
    """Carga un reporte específico por nombre de archivo."""
    # Sanitizar nombre de archivo
    safe_name = os.path.basename(filename)
    report_path = get_out_dir() / safe_name
    if not report_path.exists():
        return None

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return enrich_report_references(data)
    except Exception as e:
        logger.error("Error al cargar reporte %s: %s", filename, e)
        return None


def list_available_reports() -> List[Dict[str, str]]:
    """Lista todos los reportes disponibles en out/."""
    files = get_report_files()
    result = []
    for f in files:
        name = os.path.basename(f)
        semana = name.replace("report_", "").replace(".json", "")
        result.append({
            "filename": name,
            "semana": semana,
            "modified": datetime.fromtimestamp(os.path.getmtime(f), timezone.utc).isoformat(),
        })
    return result


def query_db_items(fuente: Optional[str] = None, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Consulta ítems almacenados en SQLite con filtros."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return []

    items = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = "SELECT fuente, titulo, resumen, url, autor, fecha, metricas_json FROM items WHERE 1=1"
        params: List[Any] = []

        if fuente and fuente.lower() != "todas":
            query += " AND LOWER(fuente) = ?"
            params.append(fuente.lower())

        if search:
            query += " AND (LOWER(titulo) LIKE ? OR LOWER(resumen) LIKE ?)"
            term = f"%{search.lower()}%"
            params.extend([term, term])

        query += " ORDER BY fecha DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        for row in cur.fetchall():
            try:
                metricas = json.loads(row["metricas_json"] or "{}")
            except Exception:
                metricas = {}
            items.append({
                "fuente": row["fuente"],
                "titulo": row["titulo"],
                "resumen": row["resumen"],
                "url": row["url"],
                "autor": row["autor"] or "Desconocido",
                "fecha": row["fecha"],
                "metricas": metricas,
            })
        conn.close()
    except Exception as e:
        logger.error("Error al consultar ítems en SQLite: %s", e)
    return items


def trigger_background_run():
    """Ejecuta el pipeline completo de Radar30X en un hilo separado."""
    global RUN_STATE

    with RUN_LOCK:
        if RUN_STATE["is_running"]:
            return False
        RUN_STATE["is_running"] = True
        RUN_STATE["last_status"] = "running"
        RUN_STATE["last_error"] = None

    def worker():
        global RUN_STATE
        try:
            logger.info("Iniciando ejecución en segundo plano de 'run.py run-all --top 10'...")
            python_bin = sys.executable
            run_script = str(get_base_dir() / "run.py")
            res = subprocess.run(
                [python_bin, run_script, "run-all", "--top", "10"],
                cwd=str(get_base_dir()),
                capture_output=True,
                text=True,
                timeout=180,
            )
            with RUN_LOCK:
                RUN_STATE["is_running"] = False
                RUN_STATE["last_run"] = datetime.now(timezone.utc).isoformat()
                if res.returncode == 0:
                    RUN_STATE["last_status"] = "success"
                else:
                    RUN_STATE["last_status"] = "error"
                    RUN_STATE["last_error"] = res.stderr or "Error desconocido durante la ejecución"
        except Exception as ex:
            with RUN_LOCK:
                RUN_STATE["is_running"] = False
                RUN_STATE["last_status"] = "error"
                RUN_STATE["last_error"] = str(ex)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return True


class RadarHTTPHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para la API JSON y la interfaz web."""

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_content: str, status: int = 200) -> None:
        payload = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 0. API: Enfoques de Búsqueda
        if path == "/api/focuses":
            from pipeline.focuses import load_focuses
            focuses = load_focuses()
            self._send_json({"focuses": [f.model_dump() for f in focuses]})
            return

        # 1. API: Listar reportes
        if path == "/api/reports":
            self._send_json({"reports": list_available_reports()})
            return

        # 2. API: Reporte más reciente
        if path == "/api/report/latest":
            data = load_latest_report()
            if data:
                self._send_json(data)
            else:
                self._send_json({"error": "No se encontraron reportes generados aún."}, status=404)
            return

        # 3. API: Reporte específico (/api/report/<nombre>)
        if path.startswith("/api/report/"):
            filename = path.replace("/api/report/", "")
            if not filename.endswith(".json"):
                filename += ".json"
            data = load_report_by_name(filename)
            if data:
                self._send_json(data)
            else:
                self._send_json({"error": f"Reporte '{filename}' no encontrado."}, status=404)
            return

        # 4. API: Explorador de ítems / base de datos
        if path == "/api/items":
            fuente = params.get("fuente", [None])[0]
            search = params.get("search", [None])[0]
            limit_str = params.get("limit", ["100"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 100
            items = query_db_items(fuente=fuente, search=search, limit=limit)
            self._send_json({"total": len(items), "items": items})
            return

        # 5. API: Estado de ejecución
        if path == "/api/status":
            with RUN_LOCK:
                self._send_json(RUN_STATE)
            return

        # 6. Servir Frontend Next.js estático (frontend/out) o template de reserva
        frontend_out = get_base_dir() / "frontend" / "out"
        if frontend_out.exists():
            rel_path = path.lstrip("/")
            if not rel_path or rel_path == "index.html":
                target_file = frontend_out / "index.html"
            else:
                target_file = frontend_out / rel_path

            if target_file.is_file():
                import mimetypes
                content_type, _ = mimetypes.guess_type(str(target_file))
                content_type = content_type or "application/octet-stream"
                if content_type.startswith("text/") or content_type in ["application/javascript", "application/json"]:
                    content_type += "; charset=utf-8"
                with open(target_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return

        # Fallback a plantilla de reserva
        if path in ["/", "/index.html"]:
            template_path = get_base_dir() / "web" / "templates" / "index.html"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._send_html(content)
            else:
                self._send_html("<h1>Error: plantilla index.html no encontrada</h1>", status=500)
            return

        # Ruta no encontrada
        self.send_error(404, "Ruta no encontrada")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # Disparar ejecución en segundo plano
        if path == "/api/run":
            started = trigger_background_run()
            if started:
                self._send_json({"status": "started", "message": "Radar iniciado en segundo plano."})
            else:
                self._send_json({"status": "already_running", "message": "Una ejecución ya está en curso."}, status=409)
            return

        # Crear nuevo enfoque de búsqueda
        if path == "/api/focuses":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                from pipeline.focuses import add_focus
                new_f = add_focus(
                    nombre=data.get("nombre", ""),
                    categoria=data.get("categoria", "general"),
                    keywords=data.get("keywords", []),
                    descripcion=data.get("descripcion", ""),
                )
                self._send_json({"status": "created", "focus": new_f.model_dump()}, status=201)
            except Exception as e:
                self._send_json({"error": f"Error al procesar solicitud: {e}"}, status=400)
            return

        # Alternar estado activo de enfoque (/api/focuses/<id>/toggle)
        if path.startswith("/api/focuses/") and path.endswith("/toggle"):
            focus_id = path.replace("/api/focuses/", "").replace("/toggle", "")
            from pipeline.focuses import toggle_focus
            updated = toggle_focus(focus_id)
            if updated:
                self._send_json({"status": "updated", "focus": updated.model_dump()})
            else:
                self._send_json({"error": f"Enfoque '{focus_id}' no encontrado."}, status=404)
            return

        self.send_error(404, "Ruta no encontrada")

    def do_PATCH(self) -> None:
        # Permitir PATCH para toggle también
        self.do_POST()

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/focuses/"):
            focus_id = path.replace("/api/focuses/", "").strip("/")
            from pipeline.focuses import delete_focus
            deleted = delete_focus(focus_id)
            if deleted:
                self._send_json({"status": "deleted", "id": focus_id})
            else:
                self._send_json({"error": f"Enfoque '{focus_id}' no encontrado."}, status=404)
            return

        self.send_error(404, "Ruta no encontrada")

    def log_message(self, format: str, *args: Any) -> None:
        # Silenciar logs ruidosos de polling
        if args and any(p in str(args[0]) for p in ["/api/status"]):
            return
        super().log_message(format, *args)


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Inicia el servidor web en el host y puerto especificados."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, RadarHTTPHandler)
    print(f"\n🚀 Servidor Web Radar30X activo en:")
    print(f"   👉 http://localhost:{port}")
    print(f"   👉 http://127.0.0.1:{port}")
    print("   Presiona Ctrl+C para detener el servidor.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor web detenido.")
        httpd.server_close()
