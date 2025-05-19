from urllib.parse import urljoin

from django.conf import settings
from rest_framework import serializers

from .models import AudioFile


class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = [
            "id",
            "uuid",
            "title",
            "description",
            "file",
            "is_public",
            "uploaded_at",
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = urljoin(settings.AUDIO_FILE_BASE_URL + "/", instance.file.name)
        return rep
