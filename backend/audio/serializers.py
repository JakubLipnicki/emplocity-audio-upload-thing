from urllib.parse import urljoin

from django.conf import settings
from rest_framework import serializers

from .models import AudioFile, Like


class AudioFileSerializer(serializers.ModelSerializer):
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()

    class Meta:
        model = AudioFile
        fields = ['id', 'uuid', 'title', 'description', 'file', 'is_public', 'uploaded_at', 'likes_count', 'dislikes_count']

    def get_likes_count(self, obj):
        return obj.likes.filter(is_liked=True).count()

    def get_dislikes_count(self, obj):
        return obj.likes.filter(is_liked=False).count()

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = urljoin(settings.AUDIO_FILE_BASE_URL + "/", instance.file.name)
        return rep


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["id", "audio_file", "is_liked", "created_at"]
        read_only_fields = ["id", "created_at"]
