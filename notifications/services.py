"""Punto único para disparar notificaciones en tiempo real desde cualquier
parte del backend (vistas, señales, comandos de management, tareas async).

Como se llama desde código síncrono, usamos async_to_sync para invocar
group_send sobre el channel layer.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def notify(user, title, body='', link=''):
    """Crea la notificación en la base y la empuja por WebSocket al grupo
    personal del usuario (user_<id>). Si el usuario no está conectado en ese
    momento, group_send simplemente no entrega a nadie: no es un error, y la
    notificación queda persistida para cuando vuelva a conectarse.
    """
    notification = Notification.objects.create(recipient=user, title=title, body=body, link=link)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user.id}',
        {'type': 'notification.new', 'notification': notification.to_dict()},
    )
    return notification
