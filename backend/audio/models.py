import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage
from value_object import ALLOWED_AUDIO_EXTENSIONS

User = get_user_model()


def validate_audio_file_extension(value):
    ext = value.name.lower().split(".")[-1]
    if f".{ext}" not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValidationError(
            f"Allowed audio file formats: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}."
        )


def audio_file_upload_to(instance, filename):
    extension = filename.split(".")[-1]
    return f"{instance.uuid}.{extension}"


class AudioFile(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="audio_files",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(
        upload_to=audio_file_upload_to,
        storage=S3Boto3Storage(),
        validators=[validate_audio_file_extension],
    )
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Like(models.Model):
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
