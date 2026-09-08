from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    UnreadCountView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification_list'),
    path('unread-count/', UnreadCountView.as_view(), name='notification_unread_count'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
]
