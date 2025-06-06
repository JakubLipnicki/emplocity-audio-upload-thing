# backend/accounts/tests.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AccountRegistrationTests(APITestCase):
    """
    Test suite for the user registration endpoint (/api/register).
    """

    def setUp(self):
        """
        Set up data common to all tests in this class.
        This method is run before each test method.
        """
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
        """
        Tests successful registration of a new user.
        Verifies HTTP status, user creation, default 'is_active' state, and response message.
        """
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
        """
        Tests an attempt to register a user with an email address that already exists.
        Expects a 400 Bad Request error.
        """
        self.client.post(self.register_url, self.user_data_valid, format="json")
        response = self.client.post(
            self.register_url, self.user_data_duplicate_email, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn("email", response.data)

    def test_register_user_missing_email(self):
        """
        Tests an attempt to register a user without providing an email address.
        Expects a 400 Bad Request error.
        """
        response = self.client.post(
            self.register_url, self.user_data_missing_email, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_user_missing_password(self):
        """
        Tests an attempt to register a user without providing a password.
        Expects a 400 Bad Request error.
        """
        response = self.client.post(
            self.register_url, self.user_data_missing_password, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)


class AccountLoginAndUserViewTests(APITestCase):
    """
    Test suite for user login (/api/login), user details (/api/user), and logout (/api/logout) endpoints.
    """

    def setUp(self):
        """
        Set up data for login, user view, and logout tests.
        Creates an active user and an inactive user.
        """
        self.login_url = reverse("login")
        self.user_details_url = reverse("user")
        self.logout_url = reverse("logout")

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
        """
        Tests successful login of an active user.
        Verifies HTTP status, response message, and the presence of JWT cookies.
        """
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
        """
        Tests login attempt for an active user with an incorrect password.
        Expects a 403 Forbidden error.
        """
        response = self.client.post(
            self.login_url, self.login_data_active_wrong_pass, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(str(response.data["detail"]), "Incorrect password!")

    def test_login_nonexistent_user(self):
        """
        Tests login attempt for a user email that does not exist in the database.
        Expects a 403 Forbidden error.
        """
        response = self.client.post(
            self.login_url, self.login_data_nonexistent_user, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(str(response.data["detail"]), "User not found!")

    def test_login_inactive_user(self):
        """
        Tests login attempt for a user whose account is not yet active.
        Expects a 403 Forbidden error.
        """
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
        """
        Tests retrieving user details for an authenticated user.
        Relies on JWTAuthentication reading the token from the cookie set by APIClient.
        """
        self.client.post(self.login_url, self.login_data_active_correct, format="json")
        response = self.client.get(self.user_details_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.active_user_email)
        self.assertEqual(response.data["name"], self.active_user.name)
        self.assertNotIn("password", response.data)

    def test_get_user_details_unauthenticated(self):
        """
        Tests attempting to retrieve user details without prior authentication (no cookie).
        Expects a 403 Forbidden error.
        """
        response = self.client.get(self.user_details_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            str(response.data["detail"]), "Nie podano danych uwierzytelniających."
        )

    def test_logout_user_success(self):
        """
        Tests successful logout of a user.
        Verifies that JWT cookies are cleared in the response.
        """
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

        # ZMIANA TUTAJ: Oczekuj liczby całkowitej 0 dla max-age
        self.assertEqual(access_cookie_after_logout["max-age"], 0)
        self.assertEqual(access_cookie_after_logout.value, "")
        self.assertEqual(refresh_cookie_after_logout["max-age"], 0)
        self.assertEqual(refresh_cookie_after_logout.value, "")
