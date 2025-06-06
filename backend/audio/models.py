# backend/audio/models.py
import uuid
import os  # Potrzebne do os.path.splitext

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage
# Zakładam, że value_object.py jest w głównym katalogu backendu lub jest dostępne w ścieżce Pythona
# Jeśli jest w backend/ to: from value_object import ALLOWED_AUDIO_EXTENSIONS
# Jeśli jest poziom wyżej: from ..value_object import ALLOWED_AUDIO_EXTENSIONS (może wymagać dostosowania importów)
# Na razie załóżmy, że jest dostępne jako:
from value_object import ALLOWED_AUDIO_EXTENSIONS  # DOSTOSUJ IMPORT, JEŚLI TRZEBA

from django.db.models.signals import post_save  # Import dla sygnałów
from django.dispatch import receiver  # Import dla dekoratora receiver
from django.conf import settings  # Import ustawień Django
import boto3  # Import boto3 do interakcji z S3/MinIO
from botocore.client import Config  # Dla konfiguracji boto3
from django.core.files.base import ContentFile  # Do zapisu flagi (choć użyjemy pola boolean)

User = get_user_model()


def validate_audio_file_extension(value):
    ext = value.name.lower().split(".")[-1]
    if f".{ext}" not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValidationError(
            f"Allowed audio file formats: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}."
        )


def audio_file_upload_to(instance, filename):
    # Przechowuje pliki na S3/MinIO jako uuid.extension
    extension = filename.split(".")[-1].lower()  # Użyj lower() dla spójności
    return f"{instance.uuid}.{extension}"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class AudioFile(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="audio_files",
        null=True,  # Pozwól na anonimowy upload, jeśli user=None w perform_create serializer'a
        blank=True,
    )
    title = models.CharField(max_length=255)  # Tego użyjemy do przyjaznej nazwy pliku
    description = models.TextField(blank=True, null=True)
    file = models.FileField(
        upload_to=audio_file_upload_to,
        storage=S3Boto3Storage(),  # Używasz S3Boto3Storage
        validators=[validate_audio_file_extension],
    )
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, related_name="audio_files", blank=True)

    # --- NOWE POLE ---
    s3_metadata_set = models.BooleanField(default=False,
                                          help_text="Indicates if Content-Disposition metadata has been set on S3/MinIO.")

    # -----------------

    def __str__(self):
        return self.title


# --- SYGNAŁ DO USTAWIANIA METADANYCH S3/MINIO ---
@receiver(post_save, sender=AudioFile)
def set_s3_content_disposition_metadata(sender, instance, created, **kwargs):
    # Ustaw metadane tylko jeśli plik istnieje i metadane nie zostały jeszcze ustawione
    # lub jeśli tytuł się zmienił (co powinno skutkować aktualizacją nazwy pliku)
    # Sprawdzamy `instance.file.name` bo samo `instance.file` może być puste przed pierwszym zapisem
    if instance.file and instance.file.name and not instance.s3_metadata_set:
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                # config=Config(signature_version='s3v4'), # Może być potrzebne dla niektórych konfiguracji MinIO/S3
                region_name=settings.AWS_S3_REGION_NAME if hasattr(settings, 'AWS_S3_REGION_NAME') else None
            )

            # Nazwa klucza obiektu w S3/MinIO (to jest uuid.extension)
            object_key = instance.file.name

            # Stwórz przyjazną nazwę pliku na podstawie tytułu i oryginalnego rozszerzenia
            # Oryginalna nazwa (z uuid) jest w instance.file.name
            _, extension = os.path.splitext(object_key)  # Pobierz rozszerzenie z nazwy pliku na S3
            # Usuń znaki, które mogą być problematyczne w nazwach plików lub nagłówkach HTTP.
            # Zastąp spacje np. podkreślnikami.
            safe_title = "".join(c if c.isalnum() or c in ['.', '-'] else '_' for c in instance.title)
            friendly_filename = f"{safe_title}{extension}"

            print(
                f"AUDIO_MODEL_SIGNAL: Attempting to set Content-Disposition for S3 object: {object_key} to filename: \"{friendly_filename}\"")

            # Użyj copy_object do aktualizacji metadanych obiektu w S3/MinIO.
            # To standardowy sposób na zmianę metadanych bez ponownego uploadu całego pliku.
            # Musimy pobrać istniejący ContentType, aby go nie nadpisać domyślnym.
            # Storage może mieć metodę do pobierania metadanych, ale użycie head_object jest bardziej uniwersalne.
            try:
                object_metadata = s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=object_key)
                current_content_type = object_metadata.get('ContentType', 'application/octet-stream')
            except Exception as e_head:
                print(
                    f"AUDIO_MODEL_SIGNAL_ERROR: Could not get current ContentType for {object_key}. Error: {e_head}. Using default.")
                current_content_type = 'application/octet-stream'

            s3_client.copy_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                CopySource={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
                # Kopiuj z tego samego miejsca
                Key=object_key,  # Zapisz w tym samym miejscu
                MetadataDirective='REPLACE',  # Ważne: zastąp istniejące metadane nowymi
                ContentType=current_content_type,  # Zachowaj oryginalny Content-Type
                ContentDisposition=f'attachment; filename="{friendly_filename}"'  # Ustaw przyjazną nazwę do pobrania
            )

            # Oznacz, że metadane zostały ustawione, aby uniknąć ponownego wywołania
            # Aktualizuj tylko to jedno pole, aby nie wywołać ponownie sygnału post_save w pętli (teoretycznie)
            AudioFile.objects.filter(pk=instance.pk).update(s3_metadata_set=True)
            print(
                f"AUDIO_MODEL_SIGNAL_SUCCESS: Successfully set Content-Disposition for {object_key} to \"{friendly_filename}\"")

        except Exception as e:
            # Zaloguj błąd, ale nie przerywaj operacji zapisu modelu, jeśli to możliwe
            print(f"AUDIO_MODEL_SIGNAL_ERROR: Error setting Content-Disposition for {object_key} in S3/MinIO: {e}")


# --- KONIEC SYGNAŁU ---


class Like(models.Model):
    # ... (reszta modelu Like bez zmian) ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    audio_file = models.ForeignKey(
        AudioFile, on_delete=models.CASCADE, related_name="likes"
    )
    is_liked = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "audio_file")

    def __str__(self):
        return f"{self.user.email} - {self.audio_file.title} - {'Like' if self.is_liked else 'Dislike'}"