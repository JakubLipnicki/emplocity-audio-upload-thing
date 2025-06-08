from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

from audio.models import AudioFile

from .models import Comment
from .serializers import CommentSerializer, ReplySerializer


class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        audio_uuid = self.kwargs["audio_uuid"]
        try:
            audio_file = AudioFile.objects.get(uuid=audio_uuid)
        except AudioFile.DoesNotExist:
            raise serializers.ValidationError("Audio file not found.")

        return Comment.objects.filter(
            audio_file_id=audio_uuid, parent_comment=None
        ).order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["audio_uuid"] = self.kwargs["audio_uuid"]
        return context


class ReplyListCreateView(generics.ListCreateAPIView):
    serializer_class = ReplySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        parent_comment = get_object_or_404(Comment, id=self.kwargs["comment_uuid"])
        return Comment.objects.filter(parent_comment=parent_comment)

    def perform_create(self, serializer):
        parent_comment = get_object_or_404(Comment, id=self.kwargs["comment_uuid"])
        serializer.save(
            user=self.request.user,
            parent_comment=parent_comment,
            audio_file_id=parent_comment.audio_file_id,
        )


class CommentRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.all()

    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.user != self.request.user:
            raise PermissionDenied("You can only edit your own comments.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("You can only delete your own comments.")
        instance.delete()
