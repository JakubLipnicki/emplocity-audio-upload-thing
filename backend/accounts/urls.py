from django.urls import path
from .views import RegisterView, UserView, LogoutView, VerifyEmailView, LoginView

urlpatterns = [
    path('register', RegisterView.as_view()),
    path('login', LoginView.as_view()),
    path('user', UserView.as_view()),
    path('logout', LogoutView.as_view()),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
]
