from django.urls import path

from .views import AudioFileDetailByUUIDView, AudioFileUploadView, LatestAudioFilesView, AudioFileDeleteView

urlpatterns = [
    path("upload/", AudioFileUploadView.as_view(), name="audio-upload"),
    path("latest/", LatestAudioFilesView.as_view(), name="audio-latest"),
    path("<uuid:uuid>/", AudioFileDetailByUUIDView.as_view(), name="audio-detail"),
    path("delete/<uuid:uuid>/", AudioFileDeleteView.as_view(), name="audio-delete"),
]
