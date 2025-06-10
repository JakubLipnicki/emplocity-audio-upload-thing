from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("admin/", admin.site.urls),
    path("api/audio/", include("audio.urls")),
    path("api/payments/", include("payments.urls", namespace="payments")),
    path("api/comments/", include("comments.urls")),
]
