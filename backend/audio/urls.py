from django.urls import path

from .views import (
    AddLikeView,
    AudioFileDeleteView,
    AudioFileDetailByUUIDView,
    AudioFileLikesCountView,
    AudioFilesByTagView,
    AudioFileUploadView,
    LatestAudioFilesView,
    TagListView,
    TopRatedAudioFilesView,
    UserLikedAudioFilesView,
    UserUploadedAudioFilesView,
)

app_name = "audio"

urlpatterns = [
    path("upload/", AudioFileUploadView.as_view(), name="audio-upload"),
    path("latest/", LatestAudioFilesView.as_view(), name="audio-latest"),
    path("<uuid:uuid>/like/", AddLikeView.as_view(), name="audio-like"),
    path(
        "<uuid:uuid>/likes-count/",
        AudioFileLikesCountView.as_view(),
        name="audio-likes-count",
    ),
    path("<uuid:uuid>/", AudioFileDetailByUUIDView.as_view(), name="audio-detail"),
    path("<uuid:uuid>/delete/", AudioFileDeleteView.as_view(), name="audio-delete"),
    path("liked/", UserLikedAudioFilesView.as_view(), name="user-liked-audio"),
    path("my-files/", UserUploadedAudioFilesView.as_view(), name="user-uploaded-files"),
    path("tags/", TagListView.as_view(), name="tag-list"),
    path("tags/<str:tag_name>/", AudioFilesByTagView.as_view(), name="audio-by-tag"),
    path("top-rated/", TopRatedAudioFilesView.as_view(), name="audio-top-rated"),
]
