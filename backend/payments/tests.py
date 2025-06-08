# backend/payments/tests.py
import hashlib  # For SHA-256 signature generation
import json

# import hmac # Not directly used in this file, but was in views.py, can be kept if planned for other tests
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PaymentOrder

# import time # Not used in current payment tests, can be removed if not needed later


User = get_user_model()


# --- Helper function to generate PayU signature for tests ---
def generate_payu_signature(data_bytes, signature_key):
    """
    Generates a PayU-style signature for a given data payload (bytes).
    Concatenates data with the key, then SHA-256 hashes it.
    """
    concatenated = data_bytes + signature_key.encode("utf-8")
    return hashlib.sha256(concatenated).hexdigest()


class PaymentInitiationTests(APITestCase):
    """
    Test suite for the payment initiation endpoint (/api/payments/initiate/).
    """

    def setUp(self):
        """
        Set up data common to all tests in this class.
        """
        self.initiate_payment_url = reverse("payments:initiate_payment_api")
        self.login_url = reverse(
            "login"
        )  # From accounts.urls, for logging in the test user

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

        # Data for a valid payment initiation request
        self.valid_payload = {
            "amount": 1000,  # Example: 10.00 PLN (amount in smallest currency unit)
            "description": "Testowa Ramka Profilowa Premium",
        }

        # Data for various invalid requests
        self.payload_missing_amount = {
            # 'amount': is missing
            "description": "Test bez kwoty"
        }
        self.payload_invalid_amount_zero = {
            "amount": 0,
            "description": "Test z kwotą zero",
        }
        self.payload_invalid_amount_negative = {
            "amount": -100,
            "description": "Test z kwotą ujemną",
        }
        self.payload_missing_description = {
            "amount": 1000
            # 'description': is missing
        }

    def _login_user_for_test(self):
        """Helper method to log in the test user via API and ensure cookies are set for self.client."""
        response = self.client.post(self.login_url, self.login_data, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, "Pre-test login failed."
        )
        # Check if access_token is available either in cookies (if LoginView sets it)
        # or in response data (if LoginView was modified to return it for easier testing).
        # Your current LoginView sets cookies only.
        self.assertTrue(
            self.client.cookies.get("access_token"),
            "Access token cookie not set after login.",
        )

    def test_initiate_payment_unauthenticated(self):
        """
        Tests attempting to initiate payment by an unauthenticated user.
        Expects a 403 Forbidden error.
        """
        response = self.client.post(
            self.initiate_payment_url, self.valid_payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # initiate_payment_view uses DRF's Response, so access data via response.data
        self.assertIn("detail", response.data)
        self.assertEqual(
            str(response.data["detail"]), "Nie podano danych uwierzytelniających."
        )

    @patch("payments.views.create_payu_order_api_call")
    def test_initiate_payment_success_authenticated(self, mock_create_payu_order):
        """
        Tests successful payment initiation by an authenticated user.
        Mocks the call to the external PayU API.
        """
        self._login_user_for_test()  # Log in the user

        mock_payu_response = {
            "orderId": "PAYU_ORDER_ID_MOCK_AUTH",
            "redirectUri": "https://secure.snd.payu.com/pay/?orderId=MOCK_AUTH_SUCCESS",
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
        """Tests initiating payment with missing amount by an authenticated user."""
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url, self.payload_missing_amount, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Amount is required.")

    def test_initiate_payment_invalid_amount_zero_authenticated(self):
        """Tests initiating payment with zero amount by an authenticated user."""
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url, self.payload_invalid_amount_zero, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("amount" in response.data["error"].lower())

    def test_initiate_payment_invalid_amount_negative_authenticated(self):
        """Tests initiating payment with negative amount by an authenticated user."""
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url,
            self.payload_invalid_amount_negative,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("amount" in response.data["error"].lower())

    def test_initiate_payment_missing_description_authenticated(self):
        """Tests initiating payment with missing description by an authenticated user."""
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url, self.payload_missing_description, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("description" in response.data["error"].lower())

    @patch("payments.views.create_payu_order_api_call")
    def test_initiate_payment_payu_api_call_fails(self, mock_create_payu_order):
        """
        Tests payment initiation when the call to PayU API service fails.
        """
        self._login_user_for_test()
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
        if db_order:
            self.assertEqual(db_order.status, PaymentOrder.Status.FAILED)
        mock_create_payu_order.assert_called_once()


class PaymentNotificationTests(APITestCase):
    """
    Test suite for the PayU notification receiver endpoint (/api/payments/notify/callback/).
    """

    def setUp(self):
        self.notify_url = reverse("payments:payu_notify_callback")
        self.user = User.objects.create_user(
            email="notifyuser@example.com",
            password="testpassword",
            name="Notify Test User",
            is_active=True,
        )
        self.order = PaymentOrder.objects.create(
            user=self.user,
            amount=1234,
            description="Test Order for Notification",
            currency="PLN",
            status=PaymentOrder.Status.PENDING,
        )
        self.payu_signature_key = settings.PAYU_SIGNATURE_KEY
        if not self.payu_signature_key:  # Fallback if not set in .env for tests
            self.payu_signature_key = "dummy_test_key_for_payments_signature"  # Use a consistent dummy for tests if settings are missing
            print(
                "WARNING: PAYMENTS_TESTS: Using fallback PAYU_SIGNATURE_KEY. Ensure it's correctly set in settings via .env for real signature logic."
            )

    def _prepare_notification_data(
        self, payu_status, ext_order_id=None, payu_order_id=None
    ):
        """Helper to create notification payload dictionary."""
        ext_order_id = ext_order_id or str(self.order.ext_order_id)
        payu_order_id = payu_order_id or "PAYU_ORDER_ID_NOTIF_TEST_DUMMY"

        return {
            "order": {
                "orderId": payu_order_id,
                "extOrderId": ext_order_id,
                "orderCreateDate": "2024-01-01T12:00:00.000+01:00",
                "notifyUrl": "https://your.public.url/api/payments/notify/callback/",
                # Example, not used by test directly
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
                "status": payu_status,
            },
        }

    def test_process_completed_notification_success(self):
        """Tests processing a successful 'COMPLETED' notification from PayU."""
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        signature = generate_payu_signature(
            notification_body_bytes, self.payu_signature_key
        )

        # Construct the OpenPayU-Signature header value
        header_value = f"signature={signature};algorithm=SHA-256;sender=checkout"

        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=header_value,  # Pass header correctly for Django test client
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.COMPLETED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_profile_frame_name, self.order.description)

    def test_process_notification_invalid_signature(self):
        """Tests processing a notification with an invalid signature."""
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        invalid_signature = generate_payu_signature(
            notification_body_bytes, "this_is_a_very_wrong_key"
        )

        header_value = f"signature={invalid_signature};algorithm=SHA-256"
        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=header_value,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)

    def test_process_notification_missing_signature_header(self):
        """Tests processing a notification with a missing signature header."""
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")

        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            # No HTTP_OPENPAYU_SIGNATURE header passed
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
        header_value = f"signature={signature};algorithm=SHA-256"

        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=header_value,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.CANCELED)
        self.user.refresh_from_db()
        if (
            self.user.active_profile_frame_name is not None
        ):  # Check only if it was ever set
            self.assertNotEqual(
                self.user.active_profile_frame_name, self.order.description
            )

    def test_process_notification_order_not_found(self):
        """Tests processing a notification for an order that does not exist in local DB."""
        notification_dict = self._prepare_notification_data(
            payu_status="COMPLETED", ext_order_id="NON_EXISTENT_ORDER_ID_123"
        )
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        signature = generate_payu_signature(
            notification_body_bytes, self.payu_signature_key
        )
        header_value = f"signature={signature};algorithm=SHA-256"

        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=header_value,
        )
        self.assertEqual(
            response.status_code, status.HTTP_200_OK
        )  # View should still return 200 OK to PayU
        self.assertIn("Order not found, acknowledged.", response.content.decode())
