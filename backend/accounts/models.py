# backend/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager  # <--- DODAJ TEN IMPORT


class User(AbstractUser):
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    username = None  # Wyłączyłeś standardowe pole username
    is_active = models.BooleanField(default=False)
    active_profile_frame_name = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "name"
    ]  # Zaktualizuj REQUIRED_FIELDS, jeśli 'name' ma być wymagane przy createsuperuser
    # Jeśli 'name' jest opcjonalne, możesz zostawić REQUIRED_FIELDS = []
    # Ale 'name' w Twoim modelu nie ma null=True, blank=True, więc prawdopodobnie jest wymagane.

    objects = CustomUserManager()  # <--- PRZYPISZ NIESTANDARDOWEGO MENEDŻERA

    def __str__(self):
        return self.email
