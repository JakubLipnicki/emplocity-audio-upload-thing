from django.urls import path

from .views import AudioFileUploadView, LatestAudioFilesView

urlpatterns = [
    path("upload/", AudioFileUploadView.as_view(), name="upload-audio"),
    path("latest/", LatestAudioFilesView.as_view(), name="latest-audio-files"),
]
