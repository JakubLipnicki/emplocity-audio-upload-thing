# backend/audio/apps.py
from django.apps import AppConfig


class AudioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audio"

    def ready(self):
        # Import signals here to ensure they are connected when the app is ready.
        import audio.models  # This will execute the @receiver decorators in models.py

        # Jeśli przeniósłbyś sygnały do osobnego pliku np. audio/signals.py, importowałbyś:
        # import audio.signals
