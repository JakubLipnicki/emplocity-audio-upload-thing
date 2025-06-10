# backend/accounts/tests.py
import time
from unittest.mock import call, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APITestCase

from .utils import generate_password_reset_token, generate_verification_token

User = get_user_model()


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

    def test_register_user_success(self):
        response = self.client.post(
            self.register_url, self.user_data_valid, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(email=self.user_data_valid["email"]).exists()
        )
        created_user = User.objects.get(email=self.user_data_valid["email"])
        self.assertFalse(created_user.is_active)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"],
            "Registration successful. Check your email to activate your account.",
        )

    def test_register_user_duplicate_email(self):
        self.client.post(self.register_url, self.user_data_valid, format="json")
        response = self.client.post(
            self.register_url, self.user_data_duplicate_email, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn("email", response.data)

    def test_register_user_missing_email(self):
        response = self.client.post(
            self.register_url, self.user_data_missing_email, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_user_missing_password(self):
        response = self.client.post(
            self.register_url, self.user_data_missing_password, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)


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

    def test_login_active_user_success(self):
        response = self.client.post(
            self.login_url, self.login_data_active_correct, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Logged in successfully")
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        access_cookie = response.cookies.get("access_token")
        self.assertTrue(access_cookie["httponly"])
        expected_secure_flag = bool(settings.SESSION_COOKIE_SECURE)
        actual_secure_flag = bool(access_cookie.get("secure"))
        self.assertEqual(actual_secure_flag, expected_secure_flag)
        self.assertEqual(access_cookie["samesite"], "Lax")

    def test_login_active_user_wrong_password(self):
        response = self.client.post(
            self.login_url, self.login_data_active_wrong_pass, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(str(response.data["detail"]), "Incorrect password!")

    def test_login_nonexistent_user(self):
        response = self.client.post(
            self.login_url, self.login_data_nonexistent_user, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(str(response.data["detail"]), "User not found!")

    def test_login_inactive_user(self):
        response = self.client.post(
            self.login_url, self.login_data_inactive_user, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            str(response.data["detail"]),
            "Account not activated. Please check your email.",
        )

    def test_get_user_details_authenticated(self):
        self.client.post(self.login_url, self.login_data_active_correct, format="json")
        response = self.client.get(self.user_details_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.active_user_email)
        self.assertEqual(response.data["name"], self.active_user.name)
        self.assertNotIn("password", response.data)

    def test_get_user_details_unauthenticated(self):
        response = self.client.get(self.user_details_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            str(response.data["detail"]), "Nie podano danych uwierzytelniających."
        )

    def test_logout_user_success(self):
        login_response = self.client.post(
            self.login_url, self.login_data_active_correct, format="json"
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", login_response.cookies)
        logout_response = self.client.post(self.logout_url, format="json")
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertIn("message", logout_response.data)
        self.assertEqual(logout_response.data["message"], "Successfully logged out.")
        self.assertIn("access_token", logout_response.cookies)
        self.assertIn("refresh_token", logout_response.cookies)
        access_cookie_after_logout = logout_response.cookies.get("access_token")
        refresh_cookie_after_logout = logout_response.cookies.get("refresh_token")
        self.assertEqual(access_cookie_after_logout["max-age"], 0)
        self.assertEqual(access_cookie_after_logout.value, "")
        self.assertEqual(refresh_cookie_after_logout["max-age"], 0)
        self.assertEqual(refresh_cookie_after_logout.value, "")

    def test_refresh_token_success(self):
        login_response = self.client.post(
            self.login_url, self.login_data_active_correct, format="json"
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh_token", login_response.cookies)
        original_access_token_cookie = login_response.cookies.get("access_token")
        time.sleep(1.1)
        refresh_response = self.client.post(self.refresh_token_url, format="json")
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("message", refresh_response.data)
        self.assertEqual(
            refresh_response.data["message"], "Access token refreshed successfully"
        )
        self.assertIn("access_token", refresh_response.cookies)
        new_access_token_cookie = refresh_response.cookies.get("access_token")
        if original_access_token_cookie:
            self.assertNotEqual(
                new_access_token_cookie.value, original_access_token_cookie.value
            )
        self.assertTrue(new_access_token_cookie["httponly"])
        self.assertEqual(
            bool(new_access_token_cookie.get("secure")),
            bool(settings.SESSION_COOKIE_SECURE),
        )
        self.assertEqual(new_access_token_cookie["samesite"], "Lax")
        self.assertEqual(
            int(new_access_token_cookie["max-age"]),
            settings.ACCESS_TOKEN_EXPIRATION_TIME_HOURS * 60 * 60,
        )

    def test_refresh_token_no_refresh_cookie(self):
        response = self.client.post(self.refresh_token_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            str(response.data["detail"]), "Refresh token not found in cookies."
        )

    def test_refresh_token_invalid_or_expired_refresh_cookie(self):
        self.client.cookies.load({"refresh_token": "invalidorexpiredtoken"})
        response = self.client.post(self.refresh_token_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertTrue(
            "Invalid or expired refresh token" in str(response.data["detail"])
        )


class AccountVerificationTests(APITestCase):
    def setUp(self):
        self.verify_email_url_name = "verify-email"
        self.user_to_verify_email = "verify@example.com"
        self.user_to_verify_password = "testpassword123"
        self.user_to_verify = User.objects.create_user(
            email=self.user_to_verify_email,
            password=self.user_to_verify_password,
            name="Verify Me User",
            is_active=False,
        )
        self.expected_frontend_redirect_base = (
            f"{settings.FRONTEND_URL.rstrip('/')}/activation"
        )

    def test_verify_email_success(self):
        token = generate_verification_token(self.user_to_verify.id)
        verification_url = reverse(self.verify_email_url_name) + f"?token={token}"
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.user_to_verify.refresh_from_db()
        self.assertTrue(self.user_to_verify.is_active)
        self.assertTrue(response.url.startswith(self.expected_frontend_redirect_base))
        self.assertIn("success=true", response.url)

    def test_verify_email_already_active(self):
        self.user_to_verify.is_active = True
        self.user_to_verify.save()
        token = generate_verification_token(self.user_to_verify.id)
        verification_url = reverse(self.verify_email_url_name) + f"?token={token}"
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith(self.expected_frontend_redirect_base))
        self.assertIn("already_active=true", response.url)

    def test_verify_email_invalid_token(self):
        invalid_token = "thisisnotavalidjwttoken"
        verification_url = (
            reverse(self.verify_email_url_name) + f"?token={invalid_token}"
        )
        with patch(
            "accounts.views.decode_verification_token",
            side_effect=AuthenticationFailed("Invalid token for test"),
        ) as mock_decode:
            response = self.client.get(verification_url)
        mock_decode.assert_called_once_with(invalid_token)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith(self.expected_frontend_redirect_base))
        self.assertIn("error=invalid_token", response.url)
        self.user_to_verify.refresh_from_db()
        self.assertFalse(self.user_to_verify.is_active)

    def test_verify_email_no_token(self):
        verification_url = reverse(self.verify_email_url_name)
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith(self.expected_frontend_redirect_base))

    def test_verify_email_token_for_nonexistent_user(self):
        non_existent_user_id = 999
        token = generate_verification_token(non_existent_user_id)
        verification_url = reverse(self.verify_email_url_name) + f"?token={token}"
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith(self.expected_frontend_redirect_base))
        self.assertIn("error=user_not_found", response.url)


class AccountPasswordResetTests(APITestCase):
    def setUp(self):
        self.request_reset_url = reverse("request-password-reset")
        self.reset_password_url = reverse("reset-password")

        self.user_email = "resetpass@example.com"
        self.user_password = "oldpassword123"
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            name="Reset Password User",
            is_active=True,
        )
        self.new_password = "newStrongPassword456!"

    @patch("accounts.views.send_mail")
    def test_request_password_reset_success(self, mock_send_mail):
        response = self.client.post(
            self.request_reset_url, {"email": self.user_email}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"],
            "If an account with this email exists and is active, a password reset link has been sent.",
        )
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(args[0], "Password Reset Request")
        self.assertIn("Click the link to reset your password:", args[1])
        self.assertEqual(args[2], settings.EMAIL_HOST_USER)
        self.assertEqual(args[3], [self.user_email])
        self.assertEqual(kwargs.get("fail_silently"), False)

    def test_request_password_reset_nonexistent_email(self):
        response = self.client.post(
            self.request_reset_url, {"email": "nobody@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    @patch("accounts.views.send_mail")
    def test_request_password_reset_inactive_user_no_email_sent(self, mock_send_mail):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.request_reset_url, {"email": self.user_email}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_not_called()

    def test_reset_password_success(self):
        reset_token = generate_password_reset_token(self.user.id)
        payload = {"token": reset_token, "new_password": self.new_password}
        response = self.client.post(self.reset_password_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"], "Password has been reset successfully."
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertFalse(self.user.check_password(self.user_password))

    def test_reset_password_invalid_token(self):
        payload = {
            "token": "thisisobviouslyaninvalidtoken",
            "new_password": self.new_password,
        }
        with patch(
            "accounts.views.decode_password_reset_token",
            side_effect=AuthenticationFailed("Invalid token for test"),
        ) as mock_decode:
            response = self.client.post(self.reset_password_url, payload, format="json")
        mock_decode.assert_called_once_with(payload["token"])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("Invalid or expired token" in response.data["error"])

    def test_reset_password_missing_token_or_password(self):
        response_no_token = self.client.post(
            self.reset_password_url, {"new_password": self.new_password}, format="json"
        )
        self.assertEqual(response_no_token.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response_no_token.data)
        self.assertEqual(
            response_no_token.data["error"], "Token and new password are required"
        )

        reset_token = generate_password_reset_token(self.user.id)
        response_no_password = self.client.post(
            self.reset_password_url, {"token": reset_token}, format="json"
        )
        self.assertEqual(response_no_password.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response_no_password.data)
        self.assertEqual(
            response_no_password.data["error"], "Token and new password are required"
        )
