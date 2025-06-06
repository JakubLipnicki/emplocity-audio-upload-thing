from django.urls import path

from .views import (
    CommentListCreateView,
    CommentRetrieveUpdateDeleteView,
    ReplyListCreateView,
)

urlpatterns = [
    path(
        "audio/<uuid:audio_uuid>/",
        CommentListCreateView.as_view(),
        name="comment-list-create",
    ),
    path(
        "<uuid:pk>/", CommentRetrieveUpdateDeleteView.as_view(), name="comment-detail"
    ),
    path(
        "<uuid:comment_uuid>/replies/",
        ReplyListCreateView.as_view(),
        name="reply-list-create",
    ),
]
