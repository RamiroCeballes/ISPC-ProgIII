"""Middleware ASGI que autentica conexiones WebSocket con el access token JWT
del proyecto (rest_framework_simplejwt), ya que la API WebSocket del navegador
no permite mandar la cabecera Authorization en el handshake.

El cliente se conecta como ws://.../ws/chat/general/?token=<access_token>.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def get_user_from_token(raw_token):
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    if not raw_token:
        return AnonymousUser()
    try:
        token = AccessToken(raw_token)
        return get_user_model().objects.get(id=token['user_id'])
    except (TokenError, get_user_model().DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Lee ?token=<access_token> del query string y resuelve scope['user']."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [None])[0]
        scope['user'] = await get_user_from_token(token)
        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(app):
    return JWTAuthMiddleware(app)
