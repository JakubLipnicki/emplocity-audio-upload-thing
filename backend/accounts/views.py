import datetime

import jwt
from decouple import config
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer
from .utils import (decode_token, decode_verification_token,
                    generate_access_token, generate_refresh_token,
                    generate_verification_token)

SECRET_KEY = config("SECRET_KEY")
EMAIL_HOST_USER = config("EMAIL_HOST_USER")


class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = generate_verification_token(user.id)
        verify_link = f"{settings.BASE_URL}/api/verify-email/?token={token}"

        send_mail(
            "Account Verification",
            f"Click the link to activate your account: {verify_link}",
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        return Response(
            {
                "message": "Registration successful. Check your email to activate your account."
            }
        )


class VerifyEmailView(APIView):
    def get(self, request):
        token = request.GET.get("token")
        frontend_redirect_url = "http://localhost:3000/activation"

        if not token:
            return redirect(frontend_redirect_url)

        user_id = decode_verification_token(token)
        if not user_id:
            return redirect(frontend_redirect_url)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect(frontend_redirect_url)

        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        return redirect(frontend_redirect_url)


class LoginView(APIView):
    def post(self, request):
        email = request.data["email"]
        password = request.data["password"]

        user = User.objects.filter(email=email).first()

        if user is None:
            raise AuthenticationFailed("User not found!")

        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect password!")

        if not user.is_active:
            raise AuthenticationFailed(
                "Account not activated. Please check your email."
            )

        access_token = generate_access_token(user.id)
        refresh_token = generate_refresh_token(user.id)

        response = Response()

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=15 * 60,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        response.data = {"message": "Logged in successfully"}

        return response


class UserView(APIView):
    def get(self, request):
        token = request.COOKIES.get("access_token")

        if not token:
            raise AuthenticationFailed("Unauthenticated")

        try:
            payload = decode_token(token, expected_type="access")
        except AuthenticationFailed:
            raise AuthenticationFailed("Unauthenticated")

        user = User.objects.filter(id=payload["user_id"]).first()
        serializer = UserSerializer(user)

        return Response(serializer.data)


class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.data = {"message": "Success"}
        return response


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"error": "Something went wrong, please try again"}, status=404
            )

        if not user.is_active:
            return Response(
                {
                    "error": "Account has not been activated, please try again after activation"
                },
                status=400,
            )

        token = generate_verification_token(user.id)
        reset_link = f"{settings.BASE_URL}/reset-password/?token={token}"

        send_mail(
            "Password Reset Request",
            f"Click the link to reset your password: {reset_link}",
            EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        return Response({"message": "Password reset link has been sent to your email"})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not token or not new_password:
            return Response(
                {"error": "Token and new password are required"}, status=400
            )

        user_id = decode_verification_token(token)
        if not user_id:
            return Response({"error": "Invalid or expired token"}, status=400)

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"error": "User not found"}, status=404)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"message": "Password has been reset successfully."})


class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            raise AuthenticationFailed("Refresh token not found")

        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except AuthenticationFailed:
            raise AuthenticationFailed("Invalid or expired refresh token")

        user_id = payload["user_id"]

        access_token = generate_access_token(user_id)
        response = Response()

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        response.data = {"message": "Access token refreshed successfully"}

        return response
