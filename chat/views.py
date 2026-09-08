from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Message, Room
from .serializers import MessageSerializer, RoomSerializer

HISTORY_LIMIT = 50


class RoomListView(generics.ListAPIView):
    """Lista las salas existentes (se crean automáticamente al conectarse por WS)."""

    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]


class RoomHistoryView(APIView):
    """Últimos HISTORY_LIMIT mensajes de una sala, en orden cronológico.

    No tiene sentido resolver esto por WebSocket: es una consulta puntual que
    se hace una sola vez al entrar a la sala.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, room_slug):
        qs = (
            Message.objects.filter(room__slug=room_slug)
            .select_related('author', 'room')
            .order_by('-created_at')[:HISTORY_LIMIT]
        )
        messages = MessageSerializer(reversed(list(qs)), many=True).data
        return Response(messages)
