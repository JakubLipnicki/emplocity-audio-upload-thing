# backend/accounts/views.py
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny  # Dodano IsAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer
from .utils import (
    decode_password_reset_token,
    decode_token,
    decode_verification_token,
    generate_access_token,
    generate_password_reset_token,
    generate_refresh_token,
    generate_verification_token,
)


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
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    def get(self, request):
        token = request.GET.get("token")
        frontend_redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/activation"
        if not token:
            return redirect(frontend_redirect_url)
        try:
            user_id = decode_verification_token(token)
        except AuthenticationFailed:
            return redirect(f"{frontend_redirect_url}?error=invalid_token")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect(f"{frontend_redirect_url}?error=user_not_found")
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            return redirect(f"{frontend_redirect_url}?success=true")
        return redirect(f"{frontend_redirect_url}?already_active=true")


class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            raise AuthenticationFailed("Email and password are required.")
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
            secure=settings.SESSION_COOKIE_SECURE,
            samesite="Lax",
            max_age=settings.ACCESS_TOKEN_EXPIRATION_TIME_HOURS * 60 * 60,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite="Lax",
            max_age=settings.REFRESH_TOKEN_EXPIRATION_TIME_DAYS * 24 * 60 * 60,
        )
        response.data = {"message": "Logged in successfully"}
        response.status_code = status.HTTP_200_OK
        return response


class UserView(APIView):
    permission_classes = [
        IsAuthenticated
    ]  # Requires user to be authenticated to access this view.

    # JWTAuthentication (default) will handle checking token from header or cookie.
    def get(self, request):
        # If execution reaches here, request.user is an authenticated User instance.
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    def post(
        self, request
    ):  # Should ideally require authentication to logout a specific session
        response = Response()
        response.delete_cookie("access_token", samesite="Lax")
        response.delete_cookie("refresh_token", samesite="Lax")
        response.data = {"message": "Successfully logged out."}
        response.status_code = status.HTTP_200_OK
        return response


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(email=email).first()
        if user and user.is_active:
            token = generate_password_reset_token(user.id)
            reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password-confirm/?token={token}"
            send_mail(
                "Password Reset Request",
                f"Click the link to reset your password: {reset_link}",
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
        return Response(
            {
                "message": "If an account with this email exists and is active, a password reset link has been sent."
            }
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        if not token or not new_password:
            return Response(
                {"error": "Token and new password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user_id = decode_password_reset_token(token)
        except AuthenticationFailed as e:
            return Response(
                {"error": f"Invalid or expired token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found for token, or token is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"message": "Password has been reset successfully."})


class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            raise AuthenticationFailed("Refresh token not found in cookies.")
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            user_id = payload["user_id"]
            user = User.objects.get(id=user_id, is_active=True)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(f"Invalid or expired refresh token: {str(e)}")
        except User.DoesNotExist:
            raise AuthenticationFailed(
                "User associated with refresh token not found or not active."
            )
        access_token = generate_access_token(user.id)
        response = Response()
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite="Lax",
            max_age=settings.ACCESS_TOKEN_EXPIRATION_TIME_HOURS * 60 * 60,
        )
        response.data = {"message": "Access token refreshed successfully"}
        response.status_code = status.HTTP_200_OK
        return response
