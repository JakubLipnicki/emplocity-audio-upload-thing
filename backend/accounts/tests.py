# backend/accounts/tests.py

import datetime
import time
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APITestCase, APIRequestFactory

import jwt

# Importy z aplikacji 'accounts'
from .authentication import JWTAuthentication
from .models import User
from .serializers import UserSerializer
from .utils import (
    generate_password_reset_token,
    generate_verification_token,
    decode_token,
    generate_access_token,
    generate_refresh_token,
    decode_verification_token,
    decode_password_reset_token,
)

User = get_user_model()


# --- Testy Jednostkowe dla Logiki Biznesowej (nie-API) ---

class TestCustomUserManager(APITestCase):
    """Testy dla menedżera CustomUserManager."""

    def test_create_user_success(self):
        user = User.objects.create_user(
            email="normal@user.com", password="foo", name="Test Name"
        )
        self.assertEqual(user.email, "normal@user.com")
        self.assertEqual(user.name, "Test Name")
        self.assertTrue(user.check_password("foo"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_active)

    def test_create_user_no_email_raises_value_error(self):
        with self.assertRaises(ValueError, msg="The Email must be set"):
            User.objects.create_user(email=None, password="foo", name="Test Name")

    def test_create_superuser_success(self):
        admin_user = User.objects.create_superuser(
            email="super@user.com", password="foo", name="Super User"
        )
        self.assertEqual(admin_user.email, "super@user.com")
        self.assertEqual(admin_user.name, "Super User")
        self.assertTrue(admin_user.check_password("foo"))
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_create_superuser_not_staff_raises_value_error(self):
        with self.assertRaises(ValueError, msg="Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email="super@user.com",
                password="foo",
                name="Super User",
                is_staff=False,
            )

    def test_create_superuser_not_superuser_raises_value_error(self):
        with self.assertRaises(
                ValueError, msg="Superuser must have is_superuser=True."
        ):
            User.objects.create_superuser(
                email="super@user.com",
                password="foo",
                name="Super User",
                is_superuser=False,
            )


class TestUserModel(APITestCase):
    """Testy dla modelu User."""

    def test_user_str_representation(self):
        user = User.objects.create_user(email="test@example.com", password="password")
        self.assertEqual(str(user), "test@example.com")


class TestUserSerializer(APITestCase):
    """Testy dla UserSerializer."""

    def setUp(self):
        self.user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
        }

    def test_serializer_create_user(self):
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()

        self.assertIsInstance(user, User)
        self.assertEqual(user.email, self.user_data["email"])
        self.assertEqual(user.name, self.user_data["name"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertFalse(user.is_active)
        self.assertIn("password", serializer.validated_data)
        self.assertNotIn("password", serializer.data)


class TestJWTUtils(APITestCase):
    """Testy dla funkcji pomocniczych JWT w utils.py."""

    def setUp(self):
        self.user = User.objects.create_user(email="jwt@test.com", password="pwd")

    def test_decode_token_success(self):
        token = generate_access_token(self.user.id)
        payload = decode_token(token, expected_type="access")
        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["type"], "access")

    def test_decode_token_expired(self):
        past_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        payload = {
            "user_id": self.user.id,
            "type": "access",
            "exp": past_time,
            "iat": past_time - datetime.timedelta(hours=1)
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        with self.assertRaisesMessage(AuthenticationFailed, "Access token expired"):
            decode_token(expired_token, expected_type="access")

    def test_decode_token_invalid_signature(self):
        token = jwt.encode(
            {"user_id": self.user.id, "type": "access"}, "wrong-secret", algorithm="HS256"
        )
        with self.assertRaisesMessage(AuthenticationFailed, "Invalid token"):
            decode_token(token, expected_type="access")

    def test_decode_token_wrong_type(self):
        refresh_token = generate_refresh_token(self.user.id)
        with self.assertRaisesMessage(AuthenticationFailed, "Invalid token type"):
            decode_token(refresh_token, expected_type="access")

    def test_decode_verification_token_expired(self):
        with override_settings(EMAIL_VERIFICATION_EXPIRATION_HOURS=-1):
            token = generate_verification_token(self.user.id)
            with self.assertRaisesMessage(AuthenticationFailed, "Verification token expired"):
                decode_verification_token(token)

    # OSTATECZNY, POPRAWNY TEST DLA LINII 64
    @patch("accounts.utils.jwt.decode")
    def test_decode_verification_token_invalid_token_error(self, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.InvalidTokenError
        with self.assertRaisesMessage(AuthenticationFailed, "Invalid verification token"):
            decode_verification_token("any-token")

    def test_decode_password_reset_token_expired(self):
        with override_settings(PASSWORD_RESET_EXPIRATION_MINUTES=-1):
            token = generate_password_reset_token(self.user.id)
            with self.assertRaisesMessage(AuthenticationFailed, "Password reset token expired"):
                decode_password_reset_token(token)

    # OSTATECZNY, POPRAWNY TEST DLA LINII 88
    @patch("accounts.utils.jwt.decode")
    def test_decode_password_reset_token_invalid_token_error(self, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.InvalidTokenError
        with self.assertRaisesMessage(AuthenticationFailed, "Invalid password reset token"):
            decode_password_reset_token("any-token")


class TestJWTAuthentication(APITestCase):
    """Testy dla klasy JWTAuthentication."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.authenticator = JWTAuthentication()
        self.user = User.objects.create_user(
            email="auth@test.com", password="pwd", is_active=True
        )
        self.inactive_user = User.objects.create_user(
            email="inactive@test.com", password="pwd", is_active=False
        )

    def test_authenticate_from_bearer_header_success(self):
        token = generate_access_token(self.user.id)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        user, auth_token = self.authenticator.authenticate(request)
        self.assertEqual(user, self.user)
        self.assertEqual(auth_token, token)

    def test_authenticate_from_cookie_success(self):
        token = generate_access_token(self.user.id)
        request = self.factory.get("/")
        request.COOKIES["access_token"] = token
        user, auth_token = self.authenticator.authenticate(request)
        self.assertEqual(user, self.user)
        self.assertEqual(auth_token, token)

    def test_no_token_returns_none(self):
        request = self.factory.get("/")
        result = self.authenticator.authenticate(request)
        self.assertIsNone(result)

    def test_malformed_header_returns_none(self):
        token = generate_access_token(self.user.id)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Token {token}")
        self.assertIsNone(self.authenticator.authenticate(request))
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer{token}")
        self.assertIsNone(self.authenticator.authenticate(request))

    def test_inactive_user_raises_exception(self):
        token = generate_access_token(self.inactive_user.id)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaisesMessage(AuthenticationFailed, "User account is inactive."):
            self.authenticator.authenticate(request)

    def test_user_not_found_raises_exception(self):
        token = generate_access_token(999)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaisesMessage(
                AuthenticationFailed, "User not found for the provided token."
        ):
            self.authenticator.authenticate(request)

    def test_token_without_user_id_raises_exception(self):
        payload = {
            "type": "access",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaisesMessage(
                AuthenticationFailed, "Token payload does not contain user_id."
        ):
            self.authenticator.authenticate(request)

    @patch('accounts.authentication.User.objects.get')
    def test_unexpected_error_during_authentication(self, mock_get_user):
        mock_get_user.side_effect = Exception("Database is down")
        token = generate_access_token(self.user.id)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

        with self.assertRaisesMessage(AuthenticationFailed, "An unexpected error occurred during authentication."):
            self.authenticator.authenticate(request)


# --- Testy Integracyjne dla Widoków API ---

class AccountRegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("register")
        self.user_data_valid = {
            "name": "Test User FullName",
            "email": "testuser@example.com",
            "password": "testpassword123",
        }
        self.user_data_duplicate_email = {
            "name": "Another Test User",
            "email": "testuser@example.com",
            "password": "anotherpassword456",
        }
        self.user_data_missing_email = {
            "name": "Test User Missing Email",
            "password": "password123",
        }
        self.user_data_missing_password = {
            "name": "Test User Missing Password",
            "email": "missingpass@example.com",
        }

    @patch("accounts.views.send_mail")
    def test_register_user_success(self, mock_send_mail):
        response = self.client.post(
            self.register_url, self.user_data_valid, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(email=self.user_data_valid["email"]).exists()
        )
        created_user = User.objects.get(email=self.user_data_valid["email"])
        self.assertFalse(created_user.is_active)
        self.assertEqual(
            response.data["message"],
            "Registration successful. Check your email to activate your account.",
        )
        mock_send_mail.assert_called_once()

    def test_register_user_duplicate_email(self):
        self.client.post(self.register_url, self.user_data_valid, format="json")
        response = self.client.post(
            self.register_url, self.user_data_duplicate_email, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user_missing_email(self):
        response = self.client.post(
            self.register_url, self.user_data_missing_email, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user_missing_password(self):
        response = self.client.post(
            self.register_url, self.user_data_missing_password, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AccountLoginAndUserViewTests(APITestCase):
    def setUp(self):
        self.login_url = reverse("login")
        self.user_details_url = reverse("user")
        self.logout_url = reverse("logout")
        self.refresh_token_url = reverse("refresh")

        self.active_user_email = "active_login@example.com"
        self.active_user_password = "testpassword123"
        self.active_user = User.objects.create_user(
            email=self.active_user_email,
            password=self.active_user_password,
            name="Active Test User",
            is_active=True,
        )
        self.inactive_user_email = "inactive_login@example.com"
        self.inactive_user_password = "anotherpassword456"
        self.inactive_user = User.objects.create_user(
            email=self.inactive_user_email,
            password=self.inactive_user_password,
            name="Inactive Test User",
            is_active=False,
        )
        self.login_data_active_correct = {
            "email": self.active_user_email,
            "password": self.active_user_password,
        }
        self.login_data_active_wrong_pass = {
            "email": self.active_user_email,
            "password": "wrongpassword123",
        }
        self.login_data_nonexistent_user = {
            "email": "iamnotregistered@example.com",
            "password": "anypassword",
        }
        self.login_data_inactive_user = {
            "email": self.inactive_user_email,
            "password": self.inactive_user_password,
        }

    def test_login_active_user_success_and_sets_cookies(self):
        response = self.client.post(
            self.login_url, self.login_data_active_correct, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertIn("csrftoken", response.cookies)

    def test_login_missing_credentials(self):
        response = self.client.post(
            self.login_url, {"email": self.active_user_email}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.post(
            self.login_url, {"password": self.active_user_password}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_active_user_wrong_password(self):
        response = self.client.post(
            self.login_url, self.login_data_active_wrong_pass, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            self.login_url, self.login_data_nonexistent_user, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_inactive_user(self):
        response = self.client.post(
            self.login_url, self.login_data_inactive_user, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_details_authenticated_via_cookie(self):
        self.client.post(self.login_url, self.login_data_active_correct, format="json")
        response = self.client.get(self.user_details_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.active_user_email)

    def test_get_user_details_authenticated_via_header(self):
        token = generate_access_token(self.active_user.id)
        response = self.client.get(
            self.user_details_url, HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_details_unauthenticated(self):
        response = self.client.get(self.user_details_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_user_success(self):
        self.client.post(self.login_url, self.login_data_active_correct, format="json")
        response = self.client.post(self.logout_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_refresh_token_success(self):
        login_response = self.client.post(
            self.login_url, self.login_data_active_correct, format="json"
        )
        original_access_token = login_response.cookies["access_token"].value
        time.sleep(1)
        refresh_response = self.client.post(self.refresh_token_url, format="json")

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        new_access_token = refresh_response.cookies["access_token"].value
        self.assertNotEqual(new_access_token, original_access_token)

    def test_refresh_token_no_refresh_cookie(self):
        response = self.client.post(self.refresh_token_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_token_invalid_or_expired_refresh_cookie(self):
        self.client.cookies.load({"refresh_token": "invalidtoken"})
        response = self.client.post(self.refresh_token_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(REFRESH_TOKEN_EXPIRATION_TIME_DAYS=-1)
    def test_refresh_token_expired(self):
        expired_refresh_token = generate_refresh_token(self.active_user.id)
        self.client.cookies.load({"refresh_token": expired_refresh_token})

        response = self.client.post(self.refresh_token_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_token_for_inactive_user(self):
        self.client.post(self.login_url, self.login_data_active_correct, format="json")
        self.active_user.is_active = False
        self.active_user.save()

        del self.client.cookies['access_token']
        response = self.client.post(self.refresh_token_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            "User associated with refresh token not found or not active.",
            str(response.data["detail"]),
        )

    def test_refresh_token_for_deleted_user(self):
        self.client.post(self.login_url, self.login_data_active_correct, format="json")
        user_id_to_delete = self.active_user.id
        User.objects.filter(id=user_id_to_delete).delete()

        del self.client.cookies['access_token']
        response = self.client.post(self.refresh_token_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            "User associated with refresh token not found or not active.",
            str(response.data["detail"]),
        )


class AccountVerificationTests(APITestCase):
    def setUp(self):
        self.verify_email_url_name = "verify-email"
        self.user_to_verify = User.objects.create_user(
            email="verify@example.com",
            password="pwd",
            name="Verify Me",
            is_active=False,
        )
        self.expected_redirect_base = f"{settings.FRONTEND_URL.rstrip('/')}/activation"

    def test_verify_email_success(self):
        token = generate_verification_token(self.user_to_verify.id)
        url = reverse(self.verify_email_url_name) + f"?token={token}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.user_to_verify.refresh_from_db()
        self.assertTrue(self.user_to_verify.is_active)
        self.assertEqual(response.url, f"{self.expected_redirect_base}?success=true")

    def test_verify_email_already_active(self):
        self.user_to_verify.is_active = True
        self.user_to_verify.save()
        token = generate_verification_token(self.user_to_verify.id)
        url = reverse(self.verify_email_url_name) + f"?token={token}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            response.url, f"{self.expected_redirect_base}?already_active=true"
        )

    def test_verify_email_invalid_token(self):
        url = reverse(self.verify_email_url_name) + "?token=invalid"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            response.url, f"{self.expected_redirect_base}?error=invalid_token"
        )

    def test_verify_email_no_token(self):
        url = reverse(self.verify_email_url_name)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, self.expected_redirect_base)

    def test_verify_email_token_for_nonexistent_user(self):
        token = generate_verification_token(999)
        url = reverse(self.verify_email_url_name) + f"?token={token}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            response.url, f"{self.expected_redirect_base}?error=user_not_found"
        )


class AccountPasswordResetTests(APITestCase):
    def setUp(self):
        self.request_reset_url = reverse("request-password-reset")
        self.reset_password_url = reverse("reset-password")
        self.user_email = "resetpass@example.com"
        self.user = User.objects.create_user(
            email=self.user_email, password="old", name="Reset", is_active=True
        )
        self.new_password = "newStrongPassword!"

    @patch("accounts.views.send_mail")
    def test_request_password_reset_success(self, mock_send_mail):
        response = self.client.post(
            self.request_reset_url, {"email": self.user_email}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()

    def test_request_password_reset_missing_email(self):
        response = self.client.post(self.request_reset_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.send_mail")
    def test_request_password_reset_nonexistent_or_inactive_user_no_email(
            self, mock_send_mail
    ):
        self.client.post(
            self.request_reset_url, {"email": "no@one.com"}, format="json"
        )
        mock_send_mail.assert_not_called()

        self.user.is_active = False
        self.user.save()
        self.client.post(
            self.request_reset_url, {"email": self.user_email}, format="json"
        )
        mock_send_mail.assert_not_called()

    def test_reset_password_success(self):
        token = generate_password_reset_token(self.user.id)
        payload = {"token": token, "new_password": self.new_password}
        response = self.client.post(self.reset_password_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_reset_password_invalid_token(self):
        payload = {"token": "invalid", "new_password": self.new_password}
        response = self.client.post(self.reset_password_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_token_for_nonexistent_user(self):
        token = generate_password_reset_token(999)
        payload = {"token": token, "new_password": self.new_password}
        response = self.client.post(self.reset_password_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_missing_token_or_password(self):
        response = self.client.post(
            self.reset_password_url, {"new_password": self.new_password}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        token = generate_password_reset_token(self.user.id)
        response = self.client.post(
            self.reset_password_url, {"token": token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)