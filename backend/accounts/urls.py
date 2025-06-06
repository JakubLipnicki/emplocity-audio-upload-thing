from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    RefreshTokenView,
    RegisterView,
    RequestPasswordResetView,
    ResetPasswordView,
    UserView,
    VerifyEmailView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("user", UserView.as_view(), name="user"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "request-password-reset/",
        RequestPasswordResetView.as_view(),
        name="request-password-reset",
    ),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
]
