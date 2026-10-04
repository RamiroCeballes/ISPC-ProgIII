#!/bin/sh
# Arranque del contenedor: espera dependencias, aplica migraciones y delega
# en el CMD (daphne). Cualquier fallo corta el arranque.
set -e

# ── Esperar a PostgreSQL ────────────────────────────────────────────────────
# En ECS con RDS la base ya está arriba, pero en compose el contenedor puede
# ganarle la carrera al healthcheck.
if [ -n "${DB_HOST}" ]; then
    echo "[entrypoint] esperando a PostgreSQL en ${DB_HOST}:${DB_PORT:-5432}..."
    timeout="${DB_WAIT_TIMEOUT:-60}"
    elapsed=0
    until python -c "
import socket, sys, os
s = socket.socket()
s.settimeout(2)
try:
    s.connect((os.environ['DB_HOST'], int(os.environ.get('DB_PORT', 5432))))
except OSError:
    sys.exit(1)
finally:
    s.close()
"; do
        elapsed=$((elapsed + 2))
        if [ "${elapsed}" -ge "${timeout}" ]; then
            echo "[entrypoint] PostgreSQL no respondió en ${timeout}s" >&2
            exit 1
        fi
        sleep 2
    done
    echo "[entrypoint] PostgreSQL disponible."
fi

# ── Migraciones ─────────────────────────────────────────────────────────────
# Con varias réplicas conviene apagarlo (RUN_MIGRATIONS=False) y correrlas como
# una tarea aparte, para que no compitan entre sí al desplegar.
if [ "${RUN_MIGRATIONS:-True}" = "True" ]; then
    echo "[entrypoint] aplicando migraciones..."
    python manage.py migrate --noinput
fi

# ── Superusuario opcional (útil para la primera puesta en marcha) ───────────
if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
    echo "[entrypoint] asegurando superusuario ${DJANGO_SUPERUSER_USERNAME}..."
    python manage.py createsuperuser --noinput || true
fi

echo "[entrypoint] iniciando: $*"
exec "$@"
