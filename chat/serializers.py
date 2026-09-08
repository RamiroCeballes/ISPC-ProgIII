from rest_framework import serializers

from .models import Message, Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'slug', 'name', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    room = serializers.CharField(source='room.slug', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'author', 'text', 'created_at']
