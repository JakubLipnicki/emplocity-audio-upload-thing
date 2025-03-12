from django.urls import path
from .views import RegisterView, LoginViev, UserView, LogoutView


urlpatterns = [
    path('register', RegisterView.as_view()),
    path('login', LoginViev.as_view()),
    path('user', UserView.as_view()),
    path('logout', LogoutView.as_view()),
]