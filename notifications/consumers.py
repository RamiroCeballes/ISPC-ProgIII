from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Notification


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Consumer de notificaciones personales: ws/notifications/.

    A diferencia del chat, el origen de los eventos no es otro socket sino
    cualquier parte del backend, que publica en el grupo personal
    user_<id> a través de notifications.services.notify().
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # Al conectar, inicializamos el contador para la campanita.
        await self.send_json({'type': 'notification.unread', 'count': await self.unread_count()})

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')

        if msg_type == 'notification.read':
            await self.mark_read(content.get('id'))
            await self.send_json({'type': 'notification.unread', 'count': await self.unread_count()})

        elif msg_type == 'notification.read_all':
            await self.mark_all_read()
            await self.send_json({'type': 'notification.unread', 'count': 0})

    # ---- handler invocado por group_send(type="notification.new") --------
    async def notification_new(self, event):
        await self.send_json({'type': 'notification.new', 'notification': event['notification']})

    # ---- acceso a la base de datos (síncrono) envuelto --------------------
    @database_sync_to_async
    def unread_count(self):
        return Notification.objects.filter(recipient=self.user, is_read=False).count()

    @database_sync_to_async
    def mark_read(self, notification_id):
        Notification.objects.filter(id=notification_id, recipient=self.user).update(is_read=True)

    @database_sync_to_async
    def mark_all_read(self):
        Notification.objects.filter(recipient=self.user, is_read=False).update(is_read=True)
