from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Message, Room

MAX_MESSAGE_LENGTH = 2000


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Consumer de una sala de chat: ws/chat/<room_slug>/.

    Requiere un usuario autenticado (ver backend.ws_auth_middleware). Todo lo
    que un cliente envía se persiste y se reparte al grupo de la sala; el
    propio emisor también recibe el mensaje de vuelta por el grupo para que
    todos los clientes muestren el mismo id/created_at que quedó en la base.
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close(code=4001)  # código propio: no autenticado
            return

        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group = f'chat_{self.room_slug}'
        self.room = await self.get_or_create_room(self.room_slug)

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.room_group,
            {'type': 'chat.presence', 'event': 'join', 'user': self.user.username},
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group'):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)
            await self.channel_layer.group_send(
                self.room_group,
                {'type': 'chat.presence', 'event': 'leave', 'user': self.user.username},
            )

    # ---- mensajes que llegan DESDE el cliente ----------------------------
    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')

        if msg_type == 'chat.message':
            text = (content.get('text') or '').strip()
            if not text or len(text) > MAX_MESSAGE_LENGTH:
                await self.send_json({'type': 'error', 'detail': 'Mensaje inválido'})
                return
            message = await self.save_message(text)
            await self.channel_layer.group_send(
                self.room_group,
                {'type': 'chat.message', 'message': message},
            )

        elif msg_type == 'chat.typing':
            await self.channel_layer.group_send(
                self.room_group,
                {
                    'type': 'chat.typing',
                    'user': self.user.username,
                    'sender_channel': self.channel_name,
                },
            )

    # ---- handlers de eventos que llegan DESDE el channel layer -----------
    async def chat_message(self, event):
        await self.send_json({'type': 'chat.message', 'message': event['message']})

    async def chat_presence(self, event):
        await self.send_json(
            {'type': 'chat.presence', 'event': event['event'], 'user': event['user']}
        )

    async def chat_typing(self, event):
        if event['sender_channel'] != self.channel_name:  # no reenviarlo a quien tipea
            await self.send_json({'type': 'chat.typing', 'user': event['user']})

    # ---- acceso a la base de datos (síncrono) envuelto --------------------
    @database_sync_to_async
    def get_or_create_room(self, slug):
        room, _ = Room.objects.get_or_create(slug=slug, defaults={'name': slug.title()})
        return room

    @database_sync_to_async
    def save_message(self, text):
        message = Message.objects.create(room=self.room, author=self.user, text=text)
        return message.to_dict()
