from django.conf import settings
from rest_framework import serializers

from .models import AudioFile


class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        file_url = instance.file.name
        base_url = settings.AUDIO_FILE_BASE_URL
        full_file_url = base_url + file_url.split("/")[-1]

        representation["file"] = full_file_url
        return representation
