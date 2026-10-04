"""Endpoints de salud para orquestadores (Docker healthcheck, ECS/ALB, k8s)."""

from django.db import connection
from django.http import JsonResponse


def liveness(request):
    """Responde 200 si el proceso está vivo. No toca dependencias externas.

    Es el endpoint que debe usar el health check del load balancer: si fallara
    por una caída de la base, el balanceador mataría tareas sanas.
    """
    return JsonResponse({'status': 'ok'})


def readiness(request):
    """Responde 200 solo si además las dependencias responden."""
    checks = {}
    ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as exc:  # noqa: BLE001 - se reporta el detalle al caller
        checks['database'] = f'error: {exc}'
        ok = False

    from django.conf import settings

    if settings.USE_REDIS_CHANNEL_LAYER:
        try:
            import redis

            redis.Redis(
                host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_connect_timeout=2
            ).ping()
            checks['redis'] = 'ok'
        except Exception as exc:  # noqa: BLE001
            checks['redis'] = f'error: {exc}'
            ok = False

    return JsonResponse({'status': 'ok' if ok else 'degraded', 'checks': checks},
                        status=200 if ok else 503)
