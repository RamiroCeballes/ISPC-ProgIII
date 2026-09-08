from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from backend.asgi import application

from .models import Notification
from .services import notify

IN_MEMORY_LAYER = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
ORIGIN_HEADERS = [(b'origin', b'http://localhost:4200')]


async def acreate_user(**kwargs):
    return await sync_to_async(User.objects.create_user)(**kwargs)


async def connect_as(user):
    token = str(AccessToken.for_user(user))
    communicator = WebsocketCommunicator(
        application, f'/ws/notifications/?token={token}', headers=ORIGIN_HEADERS
    )
    connected, _ = await communicator.connect()
    return communicator, connected


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class NotificationConsumerTests(TransactionTestCase):
    async def test_receives_unread_count_on_connect(self):
        user = await acreate_user(username='dana', password='x')
        communicator, connected = await connect_as(user)
        self.assertTrue(connected)

        response = await communicator.receive_json_from()
        self.assertEqual(response, {'type': 'notification.unread', 'count': 0})

        await communicator.disconnect()

    async def test_notify_pushes_to_connected_user(self):
        user = await acreate_user(username='eze', password='x')
        communicator, connected = await connect_as(user)
        self.assertTrue(connected)
        await communicator.receive_json_from()  # contador inicial

        await sync_to_async(notify)(user, title='Nuevo ticket', body='Te asignaron #42')

        event = await communicator.receive_json_from()
        self.assertEqual(event['type'], 'notification.new')
        self.assertEqual(event['notification']['title'], 'Nuevo ticket')

        exists = await Notification.objects.filter(recipient=user, title='Nuevo ticket').aexists()
        self.assertTrue(exists)

        await communicator.disconnect()

    async def test_mark_read_updates_unread_count(self):
        user = await acreate_user(username='fer', password='x')
        await sync_to_async(notify)(user, title='Aviso 1')
        await sync_to_async(notify)(user, title='Aviso 2')

        communicator, connected = await connect_as(user)
        self.assertTrue(connected)
        initial = await communicator.receive_json_from()
        self.assertEqual(initial['count'], 2)

        notification = await Notification.objects.filter(recipient=user).afirst()
        await communicator.send_json_to({'type': 'notification.read', 'id': notification.id})

        response = await communicator.receive_json_from()
        self.assertEqual(response, {'type': 'notification.unread', 'count': 1})

        await communicator.disconnect()
