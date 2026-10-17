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
    """Ejecuta la ingesta de todas las fuentes públicas activadas."""
    print("\n🔍 [1/3] Iniciando Ingesta de Fuentes Públicas...")
    sources = get_default_sources(include_optional=True)
    all_items = []

    for src in sources:
        try:
            print(f"  -> Conectando con {src.name}...")
            items = src.fetch(limit=35)
            all_items.extend(items)
            print(f"     ✅ {src.name}: {len(items)} ítems obtenidos.")
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


def render_terminal_report(scored_topics: List[ScoredTopic], top_n: int = 10) -> None:
    """Renderiza el Top N en terminal con formato de tabla y detalles editoriales."""
    top = scored_topics[:top_n]

    if RICH_AVAILABLE and console:
        table = Table(
            title="🎯 RADAR DE CONTENIDO 30X — TOP 10 TENDENCIAS DE IA",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", style="bold yellow", width=3, justify="right")
        table.add_column("TEMA", style="bold white", width=36)
        table.add_column("FASE", style="magenta", width=14)
        table.add_column("CREC.", style="green", width=12, justify="right")
        table.add_column("CONF.", style="cyan", width=6, justify="right")
        table.add_column("ENCAJE", style="blue", width=7, justify="right")
        table.add_column("FORMATO", style="yellow", width=13)
        table.add_column("FUENTES", style="dim", width=22)

        for i, st in enumerate(top, 1):
            short_sources = ",".join(
                s.replace(" (Captura)", "").replace("GoogleNews", "GNews").replace("HackerNews", "HN")
                for s in st.cluster.fuentes[:4]
            )
            table.add_row(
                str(i),
                st.cluster.tema_canonico[:35],
                st.decision.fase,
                st.crecimiento_label.split(" ")[0],
                f"{st.decision.confianza:.2f}",
                f"{st.decision.encaje_audiencia:.2f}",
                st.decision.formato,
                short_sources,
            )

        console.print()
        console.print(table)
        console.print()

        for i, st in enumerate(top, 1):
            content = (
                f"[bold cyan]→ Por qué:[/] {st.por_que}\n"
                f"[bold green]→ Adaptación 30X:[/] {st.adaptacion_30x}"
            )
            console.print(
                Panel(
                    content,
                    title=f"[bold yellow]#{i} {st.cluster.tema_canonico}[/]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
    else:
        # Formato fallback de terminal estándar
        header = f"{'#':<3} {'TEMA':<36} {'FASE':<15} {'CREC.':<10} {'CONF.':<7} {'ENCAJE':<7} {'FORMATO':<13} {'FUENTES'}"
        print("\n" + "=" * len(header))
        print("RADAR DE CONTENIDO 30X — TOP 10 TENDENCIAS DE IA")
        print("=" * len(header))
        print(header)
        print("-" * len(header))

        for i, st in enumerate(top, 1):
            fuentes_str = ",".join(st.cluster.fuentes[:3])
            print(
                f"{i:<3} {st.cluster.tema_canonico[:35]:<36} {st.decision.fase:<15} "
                f"{st.crecimiento_label.split(' ')[0]:<10} {st.decision.confianza:<7.2f} "
                f"{st.decision.encaje_audiencia:<7.2f} {st.decision.formato:<13} {fuentes_str}"
            )
            print(f"   -> Por qué: {st.por_que}")
            print(f"   -> Adaptación 30X: {st.adaptacion_30x}\n")


def build_and_save_report(
    scored_topics: List[ScoredTopic],
    db: Database,
    top_n: int = 10,
    output_dir: str = "out",
) -> str:
    """Genera la narrativa para el Top N, construye el JSON y lo guarda en disco y SQLite."""
    print(f"\n✍️ [3/3] Generando Adaptación Editorial 30X para el Top {top_n}...")
    top = scored_topics[:top_n]

    top_temas_data = []
    for i, st in enumerate(top, 1):
        por_que, adaptacion = generate_narrative(st.cluster, st.decision)
        st.por_que = por_que
        st.adaptacion_30x = adaptacion

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
                "adaptacion_30x": st.adaptacion_30x,
                "evidencia": st.cluster.urls_evidencia(3),
            }
        )

    now = datetime.now(timezone.utc)
    week_str = f"{now.year}-W{now.isocalendar().week:02d}"
    report_id = f"report_{week_str}"

    payload = {
        "semana": week_str,
        "generado": now.isoformat(),
        "total_clusters_evaluados": len(scored_topics),
        "top_temas": top_temas_data,
    }

    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"{report_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    db.save_report(report_id, week_str, payload)
    print(f"💾 Reporte guardado con éxito en: {out_file}")
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
                f"[bold cyan]→ Por qué:[/] {it.get('por_que')}\n"
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
            print(f"   Por qué: {it.get('por_que')}")
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

    # Serve
    serve_parser = subparsers.add_parser("serve", help="Iniciar servidor web con panel interactivo")
    serve_parser.add_argument("--port", type=int, default=8080, help="Puerto del servidor web (default: 8080)")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host del servidor (default: 0.0.0.0)")

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

    if args.command == "ingest":
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
        run_ingest(db)
        scored = run_score(db)
        if scored:
            build_and_save_report(scored, db, top_n=args.top)
            render_terminal_report(scored, top_n=args.top)


if __name__ == "__main__":
    main()
