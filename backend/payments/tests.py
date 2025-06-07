# backend/payments/tests.py
import hashlib  # For SHA-256 signature generation
import hmac  # For hmac.compare_digest
import json
import time  # For a slight delay in token refresh test
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PaymentOrder

User = get_user_model()


# --- Funkcja pomocnicza do generowania podpisu PayU dla testów ---
def generate_payu_signature(data_bytes, signature_key):
    """
    Generates a PayU-style signature for a given data payload (bytes).
    Concatenates data with the key, then SHA-256 hashes it.
    """
    concatenated = data_bytes + signature_key.encode("utf-8")
    return hashlib.sha256(concatenated).hexdigest()


class AccountRegistrationTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
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
    # ... (kod tej klasy pozostaje bez zmian) ...
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


class PaymentInitiationTests(APITestCase):
    # ... (kod tej klasy, który napisaliśmy wcześniej, pozostaje bez zmian) ...
    def setUp(self):
        self.initiate_payment_url = reverse("payments:initiate_payment_api")
        self.login_url = reverse("login")
        self.test_user_email = "paymentuser@example.com"
        self.test_user_password = "testpassword123"
        self.user = User.objects.create_user(
            email=self.test_user_email,
            password=self.test_user_password,
            name="Payment Test User",
            is_active=True,
        )
        self.login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
        }
        self.valid_payload = {
            "amount": 1000,
            "description": "Testowa Ramka Profilowa Premium",
        }
        self.payload_missing_amount = {"description": "Test bez kwoty"}
        self.payload_invalid_amount_zero = {
            "amount": 0,
            "description": "Test z kwotą zero",
        }
        self.payload_invalid_amount_negative = {
            "amount": -100,
            "description": "Test z kwotą ujemną",
        }
        self.payload_missing_description = {"amount": 1000}

    def _login_user(self):
        response = self.client.post(self.login_url, self.login_data, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, "Pre-test login failed."
        )
        self.assertTrue(
            self.client.cookies.get("access_token"),
            "Access token cookie not set after login.",
        )

    def test_initiate_payment_unauthenticated(self):
        response = self.client.post(
            self.initiate_payment_url, self.valid_payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            str(response.data["detail"]), "Nie podano danych uwierzytelniających."
        )

    @patch("payments.views.create_payu_order_api_call")
    def test_initiate_payment_success_authenticated(self, mock_create_payu_order):
        self._login_user()
        mock_payu_response = {
            "orderId": "PAYU_ORDER_ID_MOCK_123",
            "redirectUri": "https://secure.snd.payu.com/pay/?orderId=MOCK123_SUCCESS",
            "status_code_received_from_payu": 201,
        }
        mock_create_payu_order.return_value = mock_payu_response
        response = self.client.post(
            self.initiate_payment_url, self.valid_payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("redirectUri", response.data)
        self.assertEqual(
            response.data["redirectUri"], mock_payu_response["redirectUri"]
        )
        self.assertIn("payuOrderId", response.data)
        self.assertEqual(response.data["payuOrderId"], mock_payu_response["orderId"])
        internal_order_id = response.data["internalOrderId"]
        self.assertTrue(PaymentOrder.objects.filter(id=internal_order_id).exists())
        db_order = PaymentOrder.objects.get(id=internal_order_id)
        self.assertEqual(db_order.user, self.user)
        self.assertEqual(db_order.amount, self.valid_payload["amount"])
        self.assertEqual(db_order.description, self.valid_payload["description"])
        self.assertEqual(db_order.status, PaymentOrder.Status.PENDING)
        self.assertEqual(db_order.payu_order_id, mock_payu_response["orderId"])
        self.assertEqual(db_order.redirect_uri_payu, mock_payu_response["redirectUri"])
        mock_create_payu_order.assert_called_once()

    def test_initiate_payment_missing_amount_authenticated(self):
        self._login_user()
        response = self.client.post(
            self.initiate_payment_url, self.payload_missing_amount, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Amount is required.")

    def test_initiate_payment_invalid_amount_zero_authenticated(self):
        self._login_user()
        response = self.client.post(
            self.initiate_payment_url, self.payload_invalid_amount_zero, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("amount" in response.data["error"].lower())

    def test_initiate_payment_invalid_amount_negative_authenticated(self):
        self._login_user()
        response = self.client.post(
            self.initiate_payment_url,
            self.payload_invalid_amount_negative,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("amount" in response.data["error"].lower())

    def test_initiate_payment_missing_description_authenticated(self):
        self._login_user()
        response = self.client.post(
            self.initiate_payment_url, self.payload_missing_description, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("description" in response.data["error"].lower())

    @patch("payments.views.create_payu_order_api_call")
    def test_initiate_payment_payu_api_call_fails(self, mock_create_payu_order):
        self._login_user()
        mock_create_payu_order.return_value = {
            "error": "PayU API Error",
            "details": "Simulated connection timeout",
        }
        response = self.client.post(
            self.initiate_payment_url, self.valid_payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"], "Failed to initiate payment with PayU."
        )
        self.assertIn("details", response.data)
        self.assertEqual(response.data["details"], "Simulated connection timeout")
        db_order = (
            PaymentOrder.objects.filter(user=self.user).order_by("-created_at").first()
        )
        self.assertIsNotNone(db_order)
        self.assertEqual(db_order.status, PaymentOrder.Status.FAILED)
        mock_create_payu_order.assert_called_once()


# === NOWA KLASA TESTOWA PONIŻEJ ===


class PaymentNotificationTests(APITestCase):
    """
    Test suite for the PayU notification receiver endpoint (/api/payments/notify/callback/).
    """

    def setUp(self):
        self.notify_url = reverse("payments:payu_notify_callback")
        # Użytkownik i zamówienie potrzebne do testowania aktualizacji statusu
        self.user = User.objects.create_user(
            email="notifyuser@example.com",
            password="testpassword",
            name="Notify Test User",
            is_active=True,
        )
        self.order = PaymentOrder.objects.create(
            user=self.user,
            amount=1234,  # 12.34 PLN
            description="Test Order for Notification",
            currency="PLN",
            status=PaymentOrder.Status.PENDING,  # Początkowy status
        )
        # Klucz do podpisu PayU (ten sam co w settings.PAYU_SIGNATURE_KEY)
        # Dla testów można go pobrać z settings lub ustawić tutaj, ale musi być spójny.
        self.payu_signature_key = settings.PAYU_SIGNATURE_KEY
        if (
            not self.payu_signature_key
        ):  # Fallback, jeśli nie ma w settings (nie powinno się zdarzyć)
            self.payu_signature_key = "test_signature_key_fallback_for_tests"
            print(
                "WARNING: Using fallback PAYU_SIGNATURE_KEY in tests. Ensure it's set in settings via .env"
            )

    def _prepare_notification_data(
        self, payu_status, ext_order_id=None, payu_order_id=None
    ):
        """Helper to create notification payload dictionary."""
        # Domyślnie użyj danych z self.order
        ext_order_id = ext_order_id or str(self.order.ext_order_id)
        payu_order_id = (
            payu_order_id or "PAYU_ORDER_ID_NOTIF_TEST"
        )  # Przykładowe ID PayU

        return {
            "order": {
                "orderId": payu_order_id,  # ID nadane przez PayU
                "extOrderId": ext_order_id,  # Twój ID zamówienia
                "orderCreateDate": "2024-01-01T12:00:00.000+01:00",
                "notifyUrl": "https://your.public.url/api/payments/notify/callback/",
                "customerIp": "123.123.123.123",
                "merchantPosId": settings.PAYU_MERCHANT_POS_ID,
                "description": self.order.description,
                "currencyCode": "PLN",
                "totalAmount": str(self.order.amount),
                "buyer": {
                    "email": self.user.email,
                    "firstName": "Notify",
                    "lastName": "User",
                    "language": "pl",
                },
                "products": [
                    {
                        "name": self.order.description,
                        "unitPrice": str(self.order.amount),
                        "quantity": "1",
                    }
                ],
                "status": payu_status,  # Status z PayU, np. COMPLETED, CANCELED
            },
            # Można dodać 'localReceiptDateTime', 'properties' etc. jeśli są potrzebne
        }

    def test_process_completed_notification_success(self):
        """Tests processing a successful 'COMPLETED' notification from PayU."""
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        signature = generate_payu_signature(
            notification_body_bytes, self.payu_signature_key
        )

        headers = {
            "HTTP_OPENPAYU_SIGNATURE": f"signature={signature};algorithm=SHA-256;sender=checkout"
        }

        # Używamy self.client.post, ale przekazujemy dane jako 'data' (bytes) i Content-Type
        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",  # Ważne dla request.body
            **headers,  # Przekazanie nagłówków
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()  # Odśwież obiekt zamówienia z bazy
        self.assertEqual(self.order.status, PaymentOrder.Status.COMPLETED)
        # Sprawdź, czy logika biznesowa zadziałała (np. aktualizacja profilu użytkownika)
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_profile_frame_name, self.order.description)

    def test_process_notification_invalid_signature(self):
        """Tests processing a notification with an invalid signature."""
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        # Generujemy zły podpis
        invalid_signature = generate_payu_signature(
            notification_body_bytes, "wrong_key_for_signature"
        )

        headers = {
            "HTTP_OPENPAYU_SIGNATURE": f"signature={invalid_signature};algorithm=SHA-256"
        }
        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            **headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status, PaymentOrder.Status.PENDING
        )  # Status nie powinien się zmienić

    def test_process_notification_missing_signature_header(self):
        """Tests processing a notification with a missing signature header."""
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")

        # Nie dodajemy nagłówka OpenPayU-Signature
        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)

    def test_process_canceled_notification(self):
        """Tests processing a 'CANCELED' notification from PayU."""
        notification_dict = self._prepare_notification_data(payu_status="CANCELED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        signature = generate_payu_signature(
            notification_body_bytes, self.payu_signature_key
        )
        headers = {
            "HTTP_OPENPAYU_SIGNATURE": f"signature={signature};algorithm=SHA-256"
        }

        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            **headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.CANCELED)
        # Upewnij się, że logika biznesowa (np. aktualizacja ramki) nie została wykonana
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.active_profile_frame_name, self.order.description)

    def test_process_notification_order_not_found(self):
        """Tests processing a notification for an order that does not exist in local DB."""
        notification_dict = self._prepare_notification_data(
            payu_status="COMPLETED", ext_order_id="NON_EXISTENT_ORDER_ID"
        )
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        signature = generate_payu_signature(
            notification_body_bytes, self.payu_signature_key
        )
        headers = {
            "HTTP_OPENPAYU_SIGNATURE": f"signature={signature};algorithm=SHA-256"
        }

        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            **headers,
        )
        # Twój widok zwraca 200 OK, nawet jeśli zamówienie nie zostanie znalezione, aby PayU nie ponawiało
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Order not found, acknowledged.", response.content.decode())
