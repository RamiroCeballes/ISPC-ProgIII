from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/?unread=1 lista las notificaciones del usuario
    autenticado, paginadas con el PageNumberPagination global del proyecto.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get('unread') == '1':
            qs = qs.filter(is_read=False)
        return qs


class NotificationMarkReadView(APIView):
    """POST /api/notifications/<id>/read/ marca una notificación como leída."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        updated = Notification.objects.filter(pk=pk, recipient=request.user).update(is_read=True)
        if not updated:
            return Response({'detail': 'No encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationMarkAllReadView(APIView):
    """POST /api/notifications/mark-all-read/ marca todas como leídas."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnreadCountView(APIView):
    """GET /api/notifications/unread-count/ para inicializar la campanita por REST."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'count': count})
