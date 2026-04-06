from django.db import models
from django.contrib.auth.models import User
from encrypted_model_fields.fields import EncryptedCharField

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    encrypted_info = EncryptedCharField(max_length=100)  # Example encrypted field
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    reset_token = models.CharField(max_length=64, null=True, blank=True)
    reset_token_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
