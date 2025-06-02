from accounts.authentication import JWTAuthentication
from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import JWTAuthentication

from .models import AudioFile, Like, Tag
from .serializers import AudioFileSerializer, LikeSerializer, TagSerializer


class AudioFileUploadView(generics.ListCreateAPIView):
    serializer_class = AudioFileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            return AudioFile.objects.filter(user=user).order_by("-uploaded_at")
        return AudioFile.objects.filter(is_public=True).order_by("-uploaded_at")

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        is_public_raw = self.request.data.get("is_public")

        if isinstance(is_public_raw, str):
            is_public = is_public_raw.lower() == "true"
        elif isinstance(is_public_raw, bool):
            is_public = is_public_raw
        else:
            is_public = False

        serializer.save(user=user, is_public=is_public)


class LatestAudioFilesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = 10
        offset = (page - 1) * page_size
        queryset = AudioFile.objects.filter(is_public=True).order_by("-uploaded_at")
        results = list(queryset[offset:offset + page_size])
        serializer = AudioFileSerializer(results, many=True)

        has_more = queryset.count() > offset + page_size
        return Response({
            "results": serializer.data,
            "has_more": has_more,
            "page": page,
        })


class AudioFileDetailByUUIDView(generics.RetrieveAPIView):
    serializer_class = AudioFileSerializer
    lookup_field = "uuid"
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            return AudioFile.objects.filter(Q(is_public=True) | Q(user=user))
        return AudioFile.objects.filter(is_public=True)


class AudioFileDeleteView(generics.DestroyAPIView):
    serializer_class = AudioFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    lookup_field = "uuid"

    def get_queryset(self):
        return AudioFile.objects.filter(user=self.request.user)


class AddLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, uuid):
        try:
            audio_file = AudioFile.objects.get(uuid=uuid)
        except AudioFile.DoesNotExist:
            raise NotFound("Audio file not found.")

        is_liked = request.data.get("is_liked")

        if is_liked is None:
            raise ValidationError({"is_liked": "This field is required."})

        like, created = Like.objects.update_or_create(
            user=request.user,
            audio_file=audio_file,
            defaults={"is_liked": is_liked},
        )

        serializer = LikeSerializer(like)
        return Response(serializer.data)


class UserLikedAudioFilesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AudioFileSerializer

    def get_queryset(self):
        liked_audio_ids = Like.objects.filter(
            user=self.request.user, is_liked=True
        ).values_list("audio_file_id", flat=True)
        return AudioFile.objects.filter(id__in=liked_audio_ids)


class AudioFileLikesCountView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, uuid):
        try:
            audio_file = AudioFile.objects.get(uuid=uuid)
        except AudioFile.DoesNotExist:
            raise NotFound("Audio file not found.")

        likes_count = audio_file.likes.filter(is_liked=True).count()
        dislikes_count = audio_file.likes.filter(is_liked=False).count()

        return Response(
            {
                "likes": likes_count,
                "dislikes": dislikes_count,
            }
        )


class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]


class AudioFilesByTagView(generics.ListAPIView):
    serializer_class = AudioFileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        tag_name = self.kwargs["tag_name"]
        return AudioFile.objects.filter(tags__name=tag_name, is_public=True).order_by(
            "-uploaded_at"
        )
