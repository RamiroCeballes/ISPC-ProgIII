from django.urls import path

from .views import RoomHistoryView, RoomListView

urlpatterns = [
    path('rooms/', RoomListView.as_view(), name='chat_rooms'),
    path('rooms/<slug:room_slug>/history/', RoomHistoryView.as_view(), name='chat_room_history'),
]
