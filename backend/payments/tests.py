# backend/payments/tests.py
import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PaymentOrder

User = get_user_model()


def generate_payu_signature(data_bytes, signature_key):
    concatenated = data_bytes + signature_key.encode("utf-8")
    return hashlib.sha256(concatenated).hexdigest()


class PaymentInitiationTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian, jest poprawny) ...
    def setUp(self):
        self.initiate_payment_url = reverse("payments:initiate_payment_api")
        self.login_url = reverse("login")
        self.test_user_email = "paymentuser_for_payments_app@example.com"
        self.test_user_password = "testpassword123"
        self.user = User.objects.create_user(
            email=self.test_user_email,
            password=self.test_user_password,
            name="Payments App Test User",
            is_active=True,
        )
        self.login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
        }
        self.valid_payload = {
            "amount": 1000,
            "description": "Testowa Ramka Profilowa Premium (z payments tests)",
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

    def _login_user_for_test(self):
        response = self.client.post(self.login_url, self.login_data, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, "Pre-test login failed."
        )
        self.assertTrue(
            self.client.cookies.get("access_token")
            or response.data.get("access_token"),
            "Access token cookie/data not found after login.",
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
        self._login_user_for_test()
        mock_payu_response = {
            "orderId": "PAYU_ORDER_ID_MOCK_PAYMENTS_APP",
            "redirectUri": "https://secure.snd.payu.com/pay/?orderId=MOCK_PAYMENTS_APP_SUCCESS",
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
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url, self.payload_missing_amount, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Amount is required.")

    def test_initiate_payment_invalid_amount_zero_authenticated(self):
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url, self.payload_invalid_amount_zero, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("amount" in response.data["error"].lower())

    def test_initiate_payment_invalid_amount_negative_authenticated(self):
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
        self._login_user_for_test()
        response = self.client.post(
            self.initiate_payment_url, self.payload_missing_description, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertTrue("description" in response.data["error"].lower())

    @patch("payments.views.create_payu_order_api_call")
    def test_initiate_payment_payu_api_call_fails(self, mock_create_payu_order):
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
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.notify_url = reverse("payments:payu_notify_callback")
        self.user = User.objects.create_user(
            email="notifyuser_payments_app@example.com",
            password="testpassword",
            name="Notify Test User Payments",
            is_active=True,
        )
        self.order = PaymentOrder.objects.create(
            user=self.user,
            amount=1234,
            description="Test Order for Notification (payments tests)",
            currency="PLN",
            status=PaymentOrder.Status.PENDING,
        )
        self.payu_signature_key = settings.PAYU_SIGNATURE_KEY
        if not self.payu_signature_key:
            self.payu_signature_key = "test_signature_key_fallback_for_tests_payments"
            print("WARNING: Using fallback PAYU_SIGNATURE_KEY in payments/tests.py.")

    def _prepare_notification_data(
        self, payu_status, ext_order_id=None, payu_order_id=None
    ):
        ext_order_id = ext_order_id or str(self.order.ext_order_id)
        payu_order_id = payu_order_id or "PAYU_ORDER_ID_NOTIF_PAYMENTS_TEST"
        return {
            "order": {
                "orderId": payu_order_id,
                "extOrderId": ext_order_id,
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
                "status": payu_status,
            },
        }

    def test_process_completed_notification_success(self):
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        signature = generate_payu_signature(
            notification_body_bytes, self.payu_signature_key
        )
        headers = {
            "HTTP_OPENPAYU_SIGNATURE": f"signature={signature};algorithm=SHA-256;sender=checkout"
        }
        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.COMPLETED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_profile_frame_name, self.order.description)

    def test_process_notification_invalid_signature(self):
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
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
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)

    def test_process_notification_missing_signature_header(self):
        notification_dict = self._prepare_notification_data(payu_status="COMPLETED")
        notification_body_bytes = json.dumps(notification_dict).encode("utf-8")
        response = self.client.post(
            self.notify_url,
            data=notification_body_bytes,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PaymentOrder.Status.PENDING)

    def test_process_canceled_notification(self):
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
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.active_profile_frame_name, self.order.description)

    def test_process_notification_order_not_found(self):
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Order not found, acknowledged.", response.content.decode())


# === NOWA KLASA TESTOWA PONIŻEJ ===


class PaymentFinishViewTests(APITestCase):
    def setUp(self):
        self.finish_url = reverse("payments:payment_finish_page")

    def test_payment_finish_page_loads_ok_no_error(self):
        response = self.client.get(self.finish_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ZMIANA OCZEKIWANEJ ŚCIEŻKI SZABLONU
        self.assertTemplateUsed(response, "payments/payment_finish.html")
        self.assertContains(response, "Status Płatności")
        self.assertContains(response, "Twoja płatność jest przetwarzana")
        self.assertNotContains(response, "Wystąpił błąd")

    def test_payment_finish_page_with_payu_error_param(self):
        error_code = "501"
        response = self.client.get(f"{self.finish_url}?error={error_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ZMIANA OCZEKIWANEJ ŚCIEŻKI SZABLONU
        self.assertTemplateUsed(response, "payments/payment_finish.html")
        self.assertContains(response, "Status Płatności")
        self.assertContains(
            response,
            f"Wystąpił błąd podczas procesu płatności po stronie PayU (kod błędu: {error_code})",
        )
        self.assertNotContains(response, "Twoja płatność jest przetwarzana")

    # test_payment_finish_page_context_data nie używa assertTemplateUsed, więc nie wymaga zmiany w tej kwestii
    def test_payment_finish_page_context_data(self):
        response = self.client.get(self.finish_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ten test nie potrzebuje assertTemplateUsed, ale upewnij się, że widok renderuje poprawny szablon
        self.assertEqual(response.context["page_title"], "Status Płatności")
        self.assertFalse(response.context["is_error"])
        self.assertEqual(response.context["FRONTEND_URL"], settings.FRONTEND_URL)

        response_with_error = self.client.get(f"{self.finish_url}?error=some_error")
        self.assertEqual(response_with_error.status_code, status.HTTP_200_OK)
        self.assertTrue(response_with_error.context["is_error"])
