from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255) # Pamiętaj, że Django hashuje hasła, więc to pole jest zarządzane inaczej
    username = None # Wyłączyłeś standardowe pole username
    is_active = models.BooleanField(default=False) # Twoje istniejące pole

    # --- NOWE POLE (PRZYKŁAD) ---
    # Przechowuje nazwę lub identyfikator aktywnej/zakupionej ramki profilowej.
    # W bardziej złożonym systemie byłaby to relacja ForeignKey do modelu ProfileFrame.
    active_profile_frame_name = models.CharField(max_length=100, blank=True, null=True)
    # --------------------------

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email