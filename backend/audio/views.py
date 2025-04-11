from rest_framework import generics

from .models import AudioFile
from .serializers import AudioFileSerializer


class AudioFileUploadView(generics.ListCreateAPIView):
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer

    def perform_create(self, serializer):
        serializer.save()
