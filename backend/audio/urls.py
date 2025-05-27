from django.urls import path
from .views import (
    AddLikeView, AudioFileDeleteView,
    AudioFileDetailByUUIDView, AudioFileLikesCountView,
    AudioFileUploadView, LatestAudioFilesView,
    UserLikedAudioFilesView
)

urlpatterns = [
    path("upload/", AudioFileUploadView.as_view(), name="audio-upload"),
    path("latest/", LatestAudioFilesView.as_view(), name="audio-latest"),
    path("<uuid:uuid>/", AudioFileDetailByUUIDView.as_view(), name="audio-detail"),
    path("delete/<uuid:uuid>/", AudioFileDeleteView.as_view(), name="audio-delete"),
    path("<uuid:uuid>/like/", AddLikeView.as_view(), name="audio-like"),
    path("liked/", UserLikedAudioFilesView.as_view(), name="user-liked-audio"),
    path("<uuid:uuid>/likes/", AudioFileLikesCountView.as_view(), name="audio-likes-count"),
]
