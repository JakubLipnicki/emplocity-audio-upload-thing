from django.core.exceptions import ValidationError
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage


def validate_audio_file_extension(value):
    allowed_extensions = (".mp3", ".wav", ".m4a", ".ogg", ".flac")
    if not value.name.lower().endswith(allowed_extensions):
        raise ValidationError(
            f"Allowed audio file formats: {', '.join(allowed_extensions)}."
        )


class AudioFile(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(
        storage=S3Boto3Storage(), validators=[validate_audio_file_extension]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
