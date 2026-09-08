"""
ASGI config for backend project.

Reparte HTTP a la aplicación Django de siempre y WebSocket a Django Channels,
autenticado con JWT (ver ws_auth_middleware.py) y protegido por validación de
Origin.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Debe inicializarse antes de importar routing/consumers, porque estos
# importan modelos.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import chat.routing  # noqa: E402
import notifications.routing  # noqa: E402
from backend.ws_auth_middleware import JWTAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
                + notifications.routing.websocket_urlpatterns
            )
        )
    ),
})
