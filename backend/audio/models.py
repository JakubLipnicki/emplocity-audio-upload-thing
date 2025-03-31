from django.db import models
from django.core.exceptions import ValidationError
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

def validate_audio_file_extension(value):
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
    if not any(value.name.endswith(ext) for ext in allowed_extensions):
        raise ValidationError(f"Allowed audio file formats: {', '.join(allowed_extensions)}.")

def get_audio_storage():
    return S3Boto3Storage()

class AudioFile(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(storage=get_audio_storage, validators=[validate_audio_file_extension])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

