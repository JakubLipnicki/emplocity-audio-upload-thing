from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .models import AudioFile
from .serializers import AudioFileSerializer
from accounts.authentication import JWTAuthentication

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

        if not user and not is_public:
            raise PermissionError("Anonymous users must set is_public=True.")

        serializer.save(user=user, is_public=is_public)

class LatestAudioFilesView(generics.ListAPIView):
    queryset = AudioFile.objects.filter(is_public=True).order_by("-uploaded_at")[:10]
    serializer_class = AudioFileSerializer
    permission_classes = [permissions.AllowAny]

class AudioFileDetailByUUIDView(generics.RetrieveAPIView):
    serializer_class = AudioFileSerializer
    lookup_field = "uuid"
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            return AudioFile.objects.filter(Q(is_public=True) | Q(user=user))
        return AudioFile.objects.filter(Q(is_public=True) | Q(user__isnull=True))
