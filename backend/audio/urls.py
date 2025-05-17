from django.urls import path
from .views import AudioFileUploadView, LatestAudioFilesView, AudioFileDetailByUUIDView

urlpatterns = [
    path("upload/", AudioFileUploadView.as_view(), name="upload-audio"),
    path("latest/", LatestAudioFilesView.as_view(), name="latest-audio-files"),
    path("audio/<uuid:uuid>/", AudioFileDetailByUUIDView.as_view(), name="audio-detail"),
]
