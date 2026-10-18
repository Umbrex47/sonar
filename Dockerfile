# ==============================================================================
# Sonar / Radar30X - Dockerfile de Producción
# ==============================================================================
FROM python:3.14-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y el frontend pre-compilado (frontend/out)
COPY . .

# Exponer el puerto del servidor HTTP unificado
EXPOSE 8080

# Volúmenes persistentes para SQLite, borradores editoriales y reportes
VOLUME ["/app/data", "/app/drafts", "/app/out"]

# Lanzar servidor nativo Sonar
CMD ["python", "run.py", "serve", "--host", "0.0.0.0", "--port", "8080"]
