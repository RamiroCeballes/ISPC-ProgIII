# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# Etapa 1: build — instala las dependencias en un virtualenv aislado.
# Las herramientas de compilación quedan solo acá y no viajan a la imagen final.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# Etapa 2: runtime — solo el intérprete, el venv ya armado y el código.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ARG ENV_NAME=produccion

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=backend.settings \
    ENV_NAME=${ENV_NAME}

# libpq5: cliente de PostgreSQL en runtime. curl: lo usa el HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=appuser:appuser . /app

# Los estáticos se juntan en build time: la imagen queda autocontenida y el
# arranque no depende de que el filesystem sea escribible.
RUN SECRET_KEY=build-only DEBUG=False python manage.py collectstatic --noinput \
    && chown -R appuser:appuser /app/staticfiles

RUN chmod +x /app/docker-entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# daphne y no gunicorn: gunicorn es WSGI y no sostiene los WebSockets de Channels.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "backend.asgi:application"]
