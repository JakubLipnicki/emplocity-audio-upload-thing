from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment


class UserCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "name"]


class ReplySerializer(serializers.ModelSerializer):
    user = UserCommentSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "audio_file_id",
            "parent_comment",
            "content",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "audio_file_id",
            "parent_comment",
            "created_at",
        ]


class CommentSerializer(serializers.ModelSerializer):
    user = UserCommentSerializer(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "audio_file_id",
            "parent_comment",
            "content",
            "created_at",
            "replies",
        ]
        read_only_fields = [
            "id",
            "user",
            "audio_file_id",
            "created_at",
            "replies",
            "parent_comment",
        ]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["audio_file_id"] = self.context["audio_uuid"]
        return super().create(validated_data)
