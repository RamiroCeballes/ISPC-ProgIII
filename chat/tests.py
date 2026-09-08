from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from backend.asgi import application

from .models import Message, Room

IN_MEMORY_LAYER = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
ORIGIN_HEADERS = [(b'origin', b'http://localhost:4200')]


async def acreate_user(**kwargs):
    return await sync_to_async(User.objects.create_user)(**kwargs)


def ws_path(room_slug, token=None):
    path = f'/ws/chat/{room_slug}/'
    return f'{path}?token={token}' if token else path


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ChatConsumerTests(TransactionTestCase):
    async def _connect(self, user, room_slug='general'):
        token = str(AccessToken.for_user(user))
        communicator = WebsocketCommunicator(
            application, ws_path(room_slug, token), headers=ORIGIN_HEADERS
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_rejects_anonymous_user(self):
        communicator = WebsocketCommunicator(
            application, ws_path('general'), headers=ORIGIN_HEADERS
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_message_is_broadcast_and_persisted(self):
        user = await acreate_user(username='ana', password='x')
        communicator = await self._connect(user)

        await communicator.receive_json_from()  # evento de presencia "join"

        await communicator.send_json_to({'type': 'chat.message', 'text': 'hola a todos'})
        response = await communicator.receive_json_from()

        self.assertEqual(response['type'], 'chat.message')
        self.assertEqual(response['message']['text'], 'hola a todos')
        self.assertEqual(response['message']['author'], 'ana')

        exists = await Message.objects.filter(text='hola a todos', author=user).aexists()
        self.assertTrue(exists)

        await communicator.disconnect()

    async def test_room_is_created_on_first_connect(self):
        user = await acreate_user(username='bruno', password='x')
        communicator = await self._connect(user, room_slug='soporte')
        await communicator.receive_json_from()  # join

        exists = await Room.objects.filter(slug='soporte').aexists()
        self.assertTrue(exists)

        await communicator.disconnect()

    async def test_rejects_empty_message(self):
        user = await acreate_user(username='carla', password='x')
        communicator = await self._connect(user)
        await communicator.receive_json_from()  # join

        await communicator.send_json_to({'type': 'chat.message', 'text': '   '})
        response = await communicator.receive_json_from()

        self.assertEqual(response['type'], 'error')
        await communicator.disconnect()
