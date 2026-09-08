from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import notify

from .models import Message


@receiver(post_save, sender=Message)
def notify_mentions(sender, instance, created, **kwargs):
    """Notifica en tiempo real a los usuarios mencionados con @usuario en un
    mensaje de chat. Ejemplo de uso de notifications.services.notify() desde
    una señal síncrona, tal como recomienda el módulo de Channels.
    """
    if not created:
        return

    User = get_user_model()
    mentioned_usernames = {
        word.lstrip('@') for word in instance.text.split() if word.startswith('@')
    }
    if not mentioned_usernames:
        return

    for user in User.objects.filter(username__in=mentioned_usernames).exclude(id=instance.author_id):
        notify(
            user,
            title=f'{instance.author.username} te mencionó en #{instance.room.slug}',
            body=instance.text[:120],
            link=f'/chat/{instance.room.slug}',
        )
