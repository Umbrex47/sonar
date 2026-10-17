#!/usr/bin/env bash
# Radar30X — Inicio con Simplicidad Absoluta (Un Solo Comando)
set -e
cd "$(dirname "$0")"

# Activar entorno virtual de Python
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=============================================================="
echo "🎯 RADAR DE CONTENIDO 30X — SERVICIO UNIFICADO"
echo "=============================================================="
echo "• Interfaz Next.js (Origin Financial Aesthetic) + API en vivo"
echo "• Puerto único integrado: http://localhost:8080"
echo "• Presiona Ctrl+C para detener el servidor en cualquier momento"
echo "=============================================================="
echo ""

exec python run.py serve --port 8080
