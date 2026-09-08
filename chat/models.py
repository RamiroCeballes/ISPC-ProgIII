from django.conf import settings
from django.db import models


class Room(models.Model):
    """Una sala de chat identificada por un slug (p. ej. 'general', 'soporte')."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages'
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author}@{self.room.slug}: {self.text[:30]}'

    def to_dict(self):
        return {
            'id': self.id,
            'room': self.room.slug,
            'author': self.author.username,
            'text': self.text,
            'created_at': self.created_at.isoformat(),
        }
