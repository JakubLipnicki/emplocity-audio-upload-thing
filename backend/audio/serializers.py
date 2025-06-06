from urllib.parse import urljoin

from django.conf import settings
from rest_framework import serializers

from .models import AudioFile, Like, Tag


class TagSerializer(serializers.ModelSerializer):
    audio_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "audio_count"]

    def get_audio_count(self, obj):
        return obj.audio_files.count()


class AudioFileSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True
    )
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    uploader = serializers.SerializerMethodField()
    views = serializers.IntegerField(read_only=True)

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
            "likes_count",
            "dislikes_count",
            "tags",
            "uploader",
            "views",
        ]

    def create(self, validated_data):
        tags_data = validated_data.pop("tags", [])
        audio_file = AudioFile.objects.create(**validated_data)
        for tag_name in tags_data:
            tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
            audio_file.tags.add(tag_obj)
        return audio_file

    def get_likes_count(self, obj):
        return obj.likes.filter(is_liked=True).count()

    def get_dislikes_count(self, obj):
        return obj.likes.filter(is_liked=False).count()

    def get_uploader(self, obj):
        return obj.user.username if obj.user else "Anonim"

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = urljoin(settings.AUDIO_FILE_BASE_URL + "/", instance.file.name)
        rep["tags"] = [tag.name for tag in instance.tags.all()]
        return rep


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["id", "audio_file", "is_liked", "created_at"]
        read_only_fields = ["id", "created_at"]
