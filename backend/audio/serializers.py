from rest_framework import serializers
from urllib.parse import urljoin
from django.conf import settings
from .models import AudioFile

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ["id", "uuid", "title", "description", "file", "uploaded_at"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        full_file_url = urljoin(settings.AUDIO_FILE_BASE_URL + "/", instance.file.name)
        representation["file"] = full_file_url
        return representation