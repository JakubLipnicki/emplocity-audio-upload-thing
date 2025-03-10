from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from .forms import UserRegistrationForm
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def register(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return JsonResponse({"message": "Rejestracja udana!", "user_id": user.id}, status=201)
        else:
            return JsonResponse({"errors": form.errors}, status=400)

    return JsonResponse({"error": "Metoda nieobsługiwana"}, status=405)
