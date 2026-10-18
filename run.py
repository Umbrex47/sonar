#!/usr/bin/env python3
"""CLI principal para Radar de Contenido 30X.

Permite ejecutar el pipeline de descubrimiento de tendencias de forma modular:
- python run.py ingest       : Recolecta contenido público desde todas las fuentes.
- python run.py score        : Deduplica, agrupa en clusters y clasifica con Jev.
- python run.py report       : Genera la tabla final en terminal y guarda el JSON.
- python run.py run-all      : Ejecuta el flujo completo de punta a punta (< 2 min).
- python run.py demo         : Muestra el reporte precalculado para pitch a prueba de fallos.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
import sys
from typing import List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

from sources import get_default_sources
from pipeline.db import Database
from pipeline.normalize import normalize_and_deduplicate
from pipeline.topics import TopicCluster, cluster_items
from pipeline.decide import ClusterDecision, decide_cluster
from pipeline.scoring import ScoredTopic, rank_topics
from pipeline.narrative import generate_narrative

# Configurar Rich para salidas visuales en terminal
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("radar30x")


def run_ingest(db: Database) -> int:
    """Ejecuta la ingesta de todas las fuentes públicas activadas con soporte del Scraper Híbrido."""
    print("\n🔍 [1/3] Iniciando Ingesta de Fuentes Públicas con Scraper Híbrido Multi-Motor...")
    sources = get_default_sources(include_optional=True)
    all_items = []

    for src in sources:
        try:
            extra_tag = ""
            if src.name in ("WebSearch", "GoogleNews"):
                extra_tag = " (Scraper Híbrido Multi-Enfoque)"
            print(f"  -> Conectando con {src.name}{extra_tag}...")
            limit = 45 if src.name in ("WebSearch", "GoogleNews") else 35
            items = src.fetch(limit=limit)
            all_items.extend(items)
            enriched_count = sum(1 for it in items if it.metricas.get("enriquecido") == 1)
            enrich_info = f" ({enriched_count} enriquecidos con Markdown profundo)" if enriched_count > 0 else ""
            print(f"     ✅ {src.name}: {len(items)} ítems obtenidos{enrich_info}.")
        except Exception as exc:
            print(f"     ⚠️ {src.name} reportó un error: {exc}")

    inserted = db.save_items(all_items)
    print(f"\n✨ Ingesta completada: {len(all_items)} ítems recolectados, {inserted} guardados en SQLite.")
    return len(all_items)


def run_score(db: Database, similarity_threshold: float = 75.0) -> List[ScoredTopic]:
    """Ejecuta normalización, clustering con rapidfuzz, decisiones Jev y scoring."""
    print("\n🧠 [2/3] Procesando Clustering y Decisiones con Jev...")
    raw_items = db.get_all_items()
    if not raw_items:
        print("  ⚠️ No hay ítems en la base de datos. Ejecute primero 'python run.py ingest'.")
        return []

    print(f"  -> Normalizando y deduplicando {len(raw_items)} ítems...")
    unique_items = normalize_and_deduplicate(raw_items)

    print(f"  -> Agrupando en clusters temáticos (umbral token_set_ratio: {similarity_threshold}%)...")
    clusters = cluster_items(unique_items, similarity_threshold=similarity_threshold)
    print(f"  -> {len(clusters)} clusters temáticos detectados.")

    print("  -> Evaluando clusters con Jev (TypeSafe System One)...")
    decisions: List[ClusterDecision] = []
    for idx, cl in enumerate(clusters, 1):
        dec = decide_cluster(cl)
        decisions.append(dec)

    print("  -> Calculando ranking ponderado por confianza de Jev...")
    ranked = rank_topics(clusters, decisions)
    return ranked


def render_terminal_report(
    scored_topics: List[ScoredTopic],
    top_n: int = 10,
    report_file: Optional[str] = None,
) -> None:
    """Renderiza el Top N en terminal con formato de tabla y detalles editoriales."""
    top_items = []
    if report_file and os.path.exists(report_file):
        try:
            with open(report_file, "r", encoding="utf-8") as rf:
                rdata = json.load(rf)
                top_items = rdata.get("top_temas", [])[:top_n]
        except Exception:
            top_items = []

    if not top_items:
        top = scored_topics[:top_n]
        for i, st in enumerate(top, 1):
            top_items.append({
                "posicion": i,
                "tema": st.cluster.tema_canonico,
                "fase": st.decision.fase,
                "crecimiento": st.crecimiento_label,
                "confianza_jev": st.decision.confianza,
                "encaje_audiencia": st.decision.encaje_audiencia,
                "formato": st.decision.formato,
                "fuentes": st.cluster.fuentes,
                "por_que": st.por_que or "Señal emergente con tracción en fuentes públicas.",
                "por_que_audiencia": st.por_que_audiencia or "Alta relevancia para líderes y equipos en LatAm.",
                "adaptacion_30x": st.adaptacion_30x or "Recomendación editorial para 30X.",
                "cambio_posicion": getattr(st, "cambio_posicion", "="),
            })

    if RICH_AVAILABLE and console:
        table = Table(
            title="🎯 RADAR DE CONTENIDO 30X — TOP 10 TENDENCIAS DE IA",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", style="bold yellow", width=8, justify="right")
        table.add_column("TEMA", style="bold white", width=36)
        table.add_column("FASE", style="magenta", width=14)
        table.add_column("CREC.", style="green", width=12, justify="right")
        table.add_column("CONF.", style="cyan", width=6, justify="right")
        table.add_column("ENCAJE", style="blue", width=7, justify="right")
        table.add_column("FORMATO", style="yellow", width=13)
        table.add_column("FUENTES", style="dim", width=22)

        for it in top_items:
            short_sources = ",".join(
                s.replace(" (Captura)", "").replace("GoogleNews", "GNews").replace("HackerNews", "HN")
                for s in it.get("fuentes", [])[:4]
            )
            delta = it.get("cambio_posicion", "")
            pos_label = f"#{it.get('posicion')} {delta}".strip()
            table.add_row(
                pos_label,
                it.get("tema", "")[:35],
                it.get("fase", ""),
                it.get("crecimiento", "").split(" ")[0],
                f"{it.get('confianza_jev', 0.85):.2f}",
                f"{it.get('encaje_audiencia', 0.9):.2f}",
                it.get("formato", ""),
                short_sources,
            )

        console.print()
        console.print(table)
        console.print()

        for it in top_items:
            content = (
                f"[bold cyan]→ Señal:[/] {it.get('por_que')}\n"
                f"[bold magenta]→ Encaje Audiencia:[/] {it.get('por_que_audiencia')}\n"
                f"[bold green]→ Adaptación 30X:[/] {it.get('adaptacion_30x')}"
            )
            delta_badge = f" ({it.get('cambio_posicion')})" if it.get("cambio_posicion") else ""
            console.print(
                Panel(
                    content,
                    title=f"[bold yellow]#{it.get('posicion')} {it.get('tema')}{delta_badge}[/]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
    else:
        # Formato fallback de terminal estándar
        header = f"{'#':<8} {'TEMA':<36} {'FASE':<15} {'CREC.':<10} {'CONF.':<7} {'ENCAJE':<7} {'FORMATO':<13} {'FUENTES'}"
        print("\n" + "=" * len(header))
        print("RADAR DE CONTENIDO 30X — TOP 10 TENDENCIAS DE IA")
        print("=" * len(header))
        print(header)
        print("-" * len(header))

        for it in top_items:
            fuentes_str = ",".join(it.get("fuentes", [])[:3])
            delta = it.get("cambio_posicion", "")
            pos_label = f"#{it.get('posicion')} {delta}".strip()
            print(
                f"{pos_label:<8} {it.get('tema', '')[:35]:<36} {it.get('fase', ''):<15} "
                f"{it.get('crecimiento', '').split(' ')[0]:<10} {it.get('confianza_jev', 0.85):<7.2f} "
                f"{it.get('encaje_audiencia', 0.9):<7.2f} {it.get('formato', ''):<13} {fuentes_str}"
            )
            print(f"   -> Señal: {it.get('por_que')}")
            print(f"   -> Encaje Audiencia: {it.get('por_que_audiencia')}")
            print(f"   -> Adaptación 30X: {it.get('adaptacion_30x')}\n")


def build_and_save_report(
    scored_topics: List[ScoredTopic],
    db: Database,
    top_n: int = 10,
    output_dir: str = "out",
    nuevas_piezas_count: int = 0,
) -> str:
    """Genera la narrativa para el Top N, construye el JSON con embudo y auditoría Jev y lo guarda."""
    print(f"\n✍️ [3/3] Generando Adaptación Editorial 30X y Embudo de Decisiones (Top {top_n})...")
    from pipeline.scoring import partition_topics_funnel
    top, observacion_topics, descartados_topics = partition_topics_funnel(scored_topics, top_n=top_n)

    # Enriquecimiento con Scraper Híbrido (Capa 0 Jina $0 -> Capa 1 Stealth $0 -> Capa 2 ZenRows)
    print(f"\n🕸️ [Scraper Híbrido] Extrayendo contenido web profundo para los {len(top)} temas del Top...")
    from pipeline.scraper import HybridScraper
    scraper = HybridScraper(enable_jitter=False)

    top_temas_data = []
    for i, st in enumerate(top, 1):
        # Localizar la mejor URL de evidencia (descartando enlaces internos o inválidos)
        primary_url = ""
        for u in st.cluster.urls_evidencia(3):
            if u and u.startswith(("http://", "https://")) and "radar30x.internal" not in u:
                primary_url = u
                break

        contenido_profundo = None
        context_text = None

        if primary_url:
            try:
                print(f"  [{i}/{len(top)}] Raspando evidencia: {primary_url[:55]}...")
                scrape_res = scraper.scrape(primary_url, mode="auto", timeout=12.0)
                if scrape_res.status == "success" and (scrape_res.content_markdown or scrape_res.content_text):
                    context_text = (scrape_res.content_markdown or scrape_res.content_text)[:1500]
                    cost = scrape_res.cost_estimate or "$0.00"
                    tokens = scrape_res.tokens_estimate
                    method = scrape_res.method_used.upper()
                    print(f"     ✅ [{method}] {scrape_res.title[:45]} ({tokens} tokens, coste: {cost})")
                    contenido_profundo = {
                        "url": primary_url,
                        "metodo": scrape_res.method_used,
                        "titulo": scrape_res.title,
                        "tokens_estimados": tokens,
                        "costo_estimado": cost,
                        "resumen_markdown": (scrape_res.content_markdown or scrape_res.content_text)[:800],
                        "autor": scrape_res.author or "",
                    }
                else:
                    print(f"     ⚠️ [{scrape_res.method_used}] Extracción parcial: {scrape_res.error_message or 'Sin texto principal'}")
            except Exception as scrape_err:
                print(f"     ⚠️ Error raspando {primary_url[:35]}: {scrape_err}")

        por_que, por_que_audiencia, adaptacion = generate_narrative(
            st.cluster,
            st.decision,
            context_text=context_text,
        )
        st.por_que = por_que
        st.por_que_audiencia = por_que_audiencia
        st.adaptacion_30x = adaptacion

        proceso_decision = None
        if st.decision.audit:
            proceso_decision = {
                "veredicto": st.decision.audit.veredicto,
                "motivo_veredicto": st.decision.audit.motivo_veredicto,
                "palabras_clave_detectadas": st.decision.audit.palabras_clave_detectadas,
                "desglose_formula": st.decision.audit.desglose_formula,
                "preguntas": [q.model_dump() for q in st.decision.audit.preguntas],
            }

        top_temas_data.append(
            {
                "posicion": i,
                "tema": st.cluster.tema_canonico,
                "fase": st.decision.fase,
                "confianza_jev": st.decision.confianza,
                "crecimiento": st.crecimiento_label,
                "score": st.score,
                "fuentes": st.cluster.fuentes,
                "gancho": st.decision.gancho,
                "formato": st.decision.formato,
                "encaje_audiencia": st.decision.encaje_audiencia,
                "por_que": st.por_que,
                "por_que_audiencia": st.por_que_audiencia,
                "adaptacion_30x": st.adaptacion_30x,
                "evidencia": st.cluster.urls_evidencia(3),
                "contenido_profundo": contenido_profundo,
                "proceso_decision": proceso_decision,
            }
        )

    # Preparar listas del embudo de descarte y observación
    descartados_data = []
    for st in descartados_topics[:40]:
        motivo = st.decision.audit.motivo_veredicto if st.decision.audit else "Descartado por bajo score de tracción"
        descartados_data.append({
            "tema": st.cluster.tema_canonico,
            "fuentes": st.cluster.fuentes,
            "score": st.score,
            "motivo": motivo,
            "veredicto": "DESCARTADO",
        })

    observacion_data = []
    for st in observacion_topics[:30]:
        motivo = st.decision.audit.motivo_veredicto if st.decision.audit else "En observación: acumulando tracción"
        observacion_data.append({
            "tema": st.cluster.tema_canonico,
            "fuentes": st.cluster.fuentes,
            "score": st.score,
            "crecimiento": st.crecimiento_label,
            "motivo": motivo,
            "veredicto": "EN_OBSERVACION",
            "evidencia": st.cluster.urls_evidencia(3),
        })

    now = datetime.now(timezone.utc)
    week_str = f"{now.year}-W{now.isocalendar().week:02d}"
    report_id = f"report_{week_str}"
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"{report_id}.json")

    # Comparar con reporte previo para detectar deltas de ranking y novedades
    prev_positions: Dict[str, int] = {}
    if os.path.exists(out_file):
        try:
            with open(out_file, "r", encoding="utf-8") as pf:
                prev_data = json.load(pf)
                for pt in prev_data.get("top_temas", []):
                    prev_positions[pt.get("tema")] = pt.get("posicion")
        except Exception:
            pass

    nuevas_tendencias_top = 0
    for t in top_temas_data:
        tema_name = t["tema"]
        if tema_name not in prev_positions:
            t["cambio_posicion"] = "NUEVO"
            t["es_nuevo"] = True
            nuevas_tendencias_top += 1
        else:
            prev_pos = prev_positions[tema_name]
            cur_pos = t["posicion"]
            diff = prev_pos - cur_pos
            if diff > 0:
                t["cambio_posicion"] = f"+{diff}"
            elif diff < 0:
                t["cambio_posicion"] = f"{diff}"
            else:
                t["cambio_posicion"] = "="
            t["es_nuevo"] = False

    embudo_metricas = {
        "total_evaluados": len(scored_topics),
        "aprobados_top": len(top_temas_data),
        "en_observacion": len(observacion_topics),
        "descartados": len(descartados_topics),
    }

    payload = {
        "semana": week_str,
        "generado": now.isoformat(),
        "total_clusters_evaluados": len(scored_topics),
        "embudo_metricas": embudo_metricas,
        "nuevas_tendencias_top": nuevas_tendencias_top,
        "nuevas_piezas_ingestadas": nuevas_piezas_count,
        "top_temas": top_temas_data,
        "temas_en_observacion": observacion_data,
        "temas_descartados": descartados_data,
    }

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"💾 Reporte guardado con éxito en: {out_file}")
    except OSError as e:
        print(f"⚠️ No se pudo guardar archivo en disco (sandbox read-only): {e}")

    try:
        db.save_report(report_id, week_str, payload)
    except Exception as e:
        print(f"⚠️ No se pudo guardar en SQLite: {e}")
    return out_file


def show_demo_sample() -> None:
    """Muestra el reporte precalculado para demostración a prueba de fallos."""
    demo_path = "out/report_sample.json"
    if not os.path.exists(demo_path):
        print(f"⚠️ No se encontró el archivo de demostración: {demo_path}")
        return

    with open(demo_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n📢 MOSTRANDO REPORTE PRECALCULADO ({data.get('semana')}):")
    top_items = data.get("top_temas", [])

    if RICH_AVAILABLE and console:
        table = Table(
            title="🎯 RADAR DE CONTENIDO 30X — DEMO EN VIVO (PLAN B)",
            box=box.ROUNDED,
            header_style="bold cyan",
        )
        table.add_column("#", style="bold yellow", width=3, justify="right")
        table.add_column("TEMA", style="bold white", width=38)
        table.add_column("FASE", style="magenta", width=14)
        table.add_column("CREC.", style="green", width=12, justify="right")
        table.add_column("CONF.", style="cyan", width=6, justify="right")
        table.add_column("ENCAJE", style="blue", width=7, justify="right")
        table.add_column("FORMATO", style="yellow", width=13)
        table.add_column("FUENTES", style="dim", width=22)

        for it in top_items:
            short_sources = ",".join(s.replace("Manual (", "").replace(")", "") for s in it.get("fuentes", []))
            table.add_row(
                str(it.get("posicion", 1)),
                it.get("tema", "")[:37],
                it.get("fase", ""),
                it.get("crecimiento", "").split(" ")[0],
                f"{it.get('confianza_jev', 0.85):.2f}",
                f"{it.get('encaje_audiencia', 0.9):.2f}",
                it.get("formato", ""),
                short_sources[:22],
            )
        console.print(table)
        console.print()

        for it in top_items[:5]:
            content = (
                f"[bold cyan]→ Señal:[/] {it.get('por_que')}\n"
                f"[bold magenta]→ Encaje Audiencia:[/] {it.get('por_que_audiencia', 'Alta relevancia para directores y líderes en LatAm.')}\n"
                f"[bold green]→ Adaptación 30X:[/] {it.get('adaptacion_30x')}"
            )
            console.print(
                Panel(
                    content,
                    title=f"[bold yellow]#{it.get('posicion')} {it.get('tema')}[/]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
    else:
        for it in top_items:
            print(f"#{it.get('posicion')} {it.get('tema')} [{it.get('fase')}]")
            print(f"   Señal: {it.get('por_que')}")
            print(f"   Encaje Audiencia: {it.get('por_que_audiencia', 'Alta relevancia para directores y líderes en LatAm.')}")
            print(f"   Adaptación 30X: {it.get('adaptacion_30x')}\n")


def main() -> None:
    """Función de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="Radar de Contenido 30X — Descubrimiento Confiable de Tendencias de IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Ingest
    subparsers.add_parser("ingest", help="Recolectar contenido de fuentes públicas")

    # Score
    subparsers.add_parser("score", help="Deduplicar, agrupar con RapidFuzz y clasificar con Jev")

    # Report
    report_parser = subparsers.add_parser("report", help="Generar reporte y tabla en terminal")
    report_parser.add_argument("--top", type=int, default=10, help="Número de temas en el reporte (default: 10)")

    # Run-all
    run_all_parser = subparsers.add_parser("run-all", help="Ejecutar flujo completo end-to-end")
    run_all_parser.add_argument("--top", type=int, default=10, help="Número de temas en el reporte (default: 10)")

    # Demo
    subparsers.add_parser("demo", help="Mostrar reporte precalculado para pitch a prueba de fallos")

    # Cycle (Multi-agent 12h loop)
    subparsers.add_parser("cycle", help="Ejecutar ciclo de 12h con agentes (Explorador -> Historiador -> Crítico)")

    # Backfill (90-day cold start solution)
    backfill_parser = subparsers.add_parser("backfill", help="Poblar memoria histórica de 90 días para el Historiador")
    backfill_parser.add_argument("--days", type=int, default=90, help="Días de historial a poblar (default: 90)")

    # Serve
    serve_parser = subparsers.add_parser("serve", help="Iniciar servidor web con panel interactivo")
    serve_parser.add_argument("--port", type=int, default=8080, help="Puerto del servidor web (default: 8080)")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host del servidor (default: 0.0.0.0)")

    # Ask (Chatbot RAG)
    ask_parser = subparsers.add_parser("ask", help="Consultar al Chatbot RAG sobre tendencias, ganchos o saturación")
    ask_parser.add_argument("pregunta", type=str, help="Pregunta en lenguaje natural")
    ask_parser.add_argument("--show-sources", action="store_true", help="Mostrar fuentes y evidencias detalladas")
    ask_parser.add_argument("--force-level", type=str, choices=["T0", "T1", "T2"], help="Forzar nivel de ejecución")
    ask_parser.add_argument("--no-cache", action="store_true", help="Ignorar respuestas en caché")

    # Draft (Gestor de borradores)
    draft_parser = subparsers.add_parser("draft", help="Gestión de borradores editoriales a partir de narrativas")
    draft_sub = draft_parser.add_subparsers(dest="draft_action", help="Acción sobre borradores")

    # draft list
    list_draft_p = draft_sub.add_parser("list", help="Listar borradores")
    list_draft_p.add_argument("--estado", type=str, choices=["idea", "borrador", "en_revision", "aprobado", "publicado", "descartado"])

    # draft new
    new_draft_p = draft_sub.add_parser("new", help="Crear nuevo borrador")
    new_draft_p.add_argument("--narrative", type=str, help="ID de narrativa o posición en el Top")
    new_draft_p.add_argument("--titulo", type=str, help="Título editorial del borrador")
    new_draft_p.add_argument("--formato", type=str, default="video_corto", help="Formato (video_corto, carrusel, hilo, articulo)")
    new_draft_p.add_argument("--gancho", type=str, default="opinion", help="Gancho psicológico")

    # draft status
    status_draft_p = draft_sub.add_parser("status", help="Actualizar estado de un borrador")
    status_draft_p.add_argument("draft_id", type=int, help="ID del borrador")
    status_draft_p.add_argument("nuevo_estado", type=str, help="Nuevo estado (borrador, en_revision, aprobado, publicado, descartado)")

    # draft show
    show_draft_p = draft_sub.add_parser("show", help="Ver contenido de un borrador")
    show_draft_p.add_argument("draft_id", type=int, help="ID del borrador")

    # draft diff
    diff_draft_p = draft_sub.add_parser("diff", help="Ver diff Git de un borrador")
    diff_draft_p.add_argument("draft_id", type=int, help="ID del borrador")

    # Cards (Materialización de tarjetas de narrativa)
    subparsers.add_parser("cards", help="Materializar tarjetas de narrativa para RAG en SQLite")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "demo":
        show_demo_sample()
        return

    if args.command == "serve":
        from web.server import run_server
        run_server(host=args.host, port=args.port)
        return

    db = Database()

    if args.command == "ask":
        from chat.service import ChatService
        service = ChatService(db=db)
        res = service.ask(
            pregunta=args.pregunta,
            no_cache=args.no_cache,
            force_level=args.force_level,
            show_sources=args.show_sources,
        )
        print(f"\n{res['respuesta']}")
        meta_info = f"\n[Nivel: {res['nivel']} | Intención: {res['intencion']} | Confianza: {int(res['confianza']*100)}% | Latencia: {res['latencia_ms']} ms"
        if res.get("desde_cache"):
            meta_info += " (desde caché)"
        meta_info += "]"
        print(meta_info)

        if args.show_sources and res.get("fuentes"):
            print("\n📚 Fuentes y Evidencias Verificadas:")
            for s in res["fuentes"]:
                print(f"  - {s}")
    elif args.command == "draft":
        from drafts.manager import DraftManager
        dm = DraftManager(db=db)
        action = getattr(args, "draft_action", None)
        if not action or action == "list":
            estado = getattr(args, "estado", None)
            drafts = dm.list_drafts(estado=estado)
            print(f"\n📝 Borradores Editoriales ({len(drafts)} encontrados):\n")
            if not drafts:
                print("  No hay borradores registrados. Cree uno con 'python run.py draft new --narrative <id>'.")
            else:
                for d in drafts:
                    print(f"  #{d['id']} [{d['estado'].upper()}] {d['titulo']} (Formato: {d['formato']}, Gancho: {d['gancho']})")
                    print(f"     Path: {d['path']}")
        elif action == "new":
            res = dm.create_draft(
                narrative_id=args.narrative,
                titulo=args.titulo,
                formato=args.formato,
                gancho=args.gancho,
            )
            print(f"\n✨ Borrador #{res['id']} creado con éxito en estado '{res['estado']}':")
            print(f"  Título: {res['titulo']}")
            print(f"  Archivo: {res['path']}")
        elif action == "status":
            try:
                res = dm.update_status(args.draft_id, args.nuevo_estado)
                print(f"\n✅ Borrador #{res['id']} actualizado:")
                print(f"  Estado: {res['estado_anterior']} -> {res['nuevo_estado']}")
                print(f"  Archivo: {res['path']}")
            except ValueError as ex:
                print(f"\n❌ Error al actualizar estado: {ex}")
        elif action == "show":
            res = dm.get_draft(args.draft_id)
            if not res:
                print(f"\n❌ Borrador #{args.draft_id} no encontrado.")
            else:
                print(f"\n--- BORRADOR #{res['id']}: {res['titulo']} ---")
                print(res.get("content", ""))
        elif action == "diff":
            diff_text = dm.get_diff(args.draft_id)
            print(f"\n--- DIFF HISTÓRICO BORRADOR #{args.draft_id} ---")
            print(diff_text)
    elif args.command == "cards":
        from pipeline.cards import materialize_all_narrative_cards
        n = materialize_all_narrative_cards(db=db)
        print(f"\n✨ {n} tarjetas de narrativa materializadas exitosamente en SQLite.")
    elif args.command == "cycle":
        from orchestrator import Orchestrator
        orch = Orchestrator(db=db)
        res = orch.run_cycle()
        if res.get("ok"):
            print(f"\n✨ Ciclo multi-agente completado con éxito (run_id: {res['run_id']}).")
            print(f"Reporte generado en: {res['report_file']}")
        else:
            print(f"\n❌ Error en ciclo multi-agente: {res.get('error')}")
    elif args.command == "backfill":
        from orchestrator import Orchestrator
        orch = Orchestrator(db=db)
        res = orch.run_backfill(days=args.days)
        if res.get("ok"):
            print(f"\n✨ Backfill de {args.days} días completado con éxito (run_id: {res['run_id']}).")
            print(f"Ítems únicos indexados en memoria: {res['stats']['unicos_guardados']}.")
        else:
            print(f"\n❌ Error en backfill: {res.get('error')}")
    elif args.command == "ingest":
        run_ingest(db)
    elif args.command == "score":
        scored = run_score(db)
        print(f"\n✅ {len(scored)} temas evaluados y clasificados.")
    elif args.command == "report":
        scored = run_score(db)
        if scored:
            build_and_save_report(scored, db, top_n=args.top)
            render_terminal_report(scored, top_n=args.top)
    elif args.command == "run-all":
        count = run_ingest(db)
        scored = run_score(db)
        if scored:
            build_and_save_report(scored, db, top_n=args.top, nuevas_piezas_count=count)
            render_terminal_report(scored, top_n=args.top)


if __name__ == "__main__":
    main()
