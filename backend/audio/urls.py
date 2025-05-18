from django.urls import path
from .views import AudioFileUploadView, LatestAudioFilesView, AudioFileDetailByUUIDView

urlpatterns = [
    path("upload/", AudioFileUploadView.as_view(), name="audio-upload"),
    path("latest/", LatestAudioFilesView.as_view(), name="audio-latest"),
    path("<uuid:uuid>/", AudioFileDetailByUUIDView.as_view(), name="audio-detail"),
]
