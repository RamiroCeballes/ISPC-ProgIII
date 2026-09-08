from django.contrib import admin

from .models import Message, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'created_at')
    search_fields = ('slug', 'name')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'author', 'text', 'created_at')
    list_filter = ('room',)
    search_fields = ('text', 'author__username')
