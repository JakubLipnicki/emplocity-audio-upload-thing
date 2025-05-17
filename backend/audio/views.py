from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AudioFile
from .serializers import AudioFileSerializer
from rest_framework.permissions import IsAuthenticated


class AudioFileUploadView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AudioFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AudioFile.objects.filter(user=self.request.user).order_by("-uploaded_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LatestAudioFilesView(generics.ListAPIView):
    queryset = AudioFile.objects.all().order_by("-uploaded_at")[:10]
    serializer_class = AudioFileSerializer

class AudioFileDetailByUUIDView(generics.RetrieveAPIView):
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer
    lookup_field = "uuid"
