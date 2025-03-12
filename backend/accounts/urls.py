from django.urls import path
from .views import RegisterView, LoginViev, UserView


urlpatterns = [
    path('register', RegisterView.as_view()),
    path('login', LoginViev.as_view()),
    path('user', UserView.as_view()),
]