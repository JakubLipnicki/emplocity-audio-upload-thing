from django.core.exceptions import ValidationError
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage

from value_object import ALLOWED_AUDIO_EXTENSIONS


def validate_audio_file_extension(value):
    if not value.name.lower().endswith(ALLOWED_AUDIO_EXTENSIONS):
        raise ValidationError(
            f"Allowed audio file formats: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}."
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
