# payments/views.py
import json
import hashlib
import hmac

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth import get_user_model  # Potrzebne do pobrania modelu User

from .models import PaymentOrder
from .payu_service import create_payu_order_api_call


@csrf_exempt
@require_POST
def initiate_payment_view(request):
    """
    API view to initiate a payment with PayU.
    Expects JSON: {'amount': (int, grosze), 'description': (str)}
    !!! AUTORYZACJA TYMCZASOWO WYŁĄCZONA DLA CELÓW TESTOWYCH PAYU !!!
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        amount = int(data.get('amount'))
        description = data.get('description')

        if not amount or amount <= 0:
            return JsonResponse({'error': 'Invalid amount (must be positive integer in grosze).'}, status=400)
        if not description:
            return JsonResponse({'error': 'Description is required.'}, status=400)

        # --- TYMCZASOWE WYŁĄCZENIE SPRAWDZANIA AUTORYZACJI ---
        # current_user = request.user
        # if not current_user.is_authenticated:
        #     return JsonResponse({'error': 'User authentication required.'}, status=401)
        # --- KONIEC TYMCZASOWEGO WYŁĄCZENIA ---

        # --- TYMCZASOWE USTAWIENIE UŻYTKOWNIKA DLA TESTÓW ---
        # ZASTĄP "twoj_istniejacy_email_testowy@example.com" RZECZYWISTYM EMAILEM
        # UŻYTKOWNIKA TESTOWEGO Z TWOJEJ BAZY DANYCH.
        # TEN UŻYTKOWNIK MUSI ISTNIEĆ.
        User = get_user_model()
        try:
            # ZMIEŃ PONIŻSZY EMAIL NA EMAIL ISTNIEJĄCEGO UŻYTKOWNIKA W TWOJEJ BAZIE
            current_user = User.objects.get(email="emplocity.project@gmail.com")
        except User.DoesNotExist:
            print(
                "PAYMENTS_VIEW_CRITICAL: Test user with specified email not found for payment initiation when auth is bypassed. Payment cannot be linked to a user.")
            return JsonResponse({
                                    'error': 'Critical Test Setup Error: Test user not found. Please configure a valid test user email in payments/views.py or fix authentication.'},
                                status=500)
        except Exception as e_user_fetch:
            print(f"PAYMENTS_VIEW_CRITICAL: Error fetching test user: {e_user_fetch}")
            return JsonResponse({'error': 'Critical Test Setup Error: Could not fetch test user.'}, status=500)
        # --- KONIEC TYMCZASOWEGO USTAWIENIA UŻYTKOWNIKA ---

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"PAYMENTS_VIEW_ERROR: Invalid JSON/data in initiate_payment_view: {str(e)}")
        return JsonResponse({'error': f'Invalid JSON payload or data type: {str(e)}'}, status=400)
    # Usunięto `except AttributeError` dla `request.user`, bo teraz `current_user` jest ustawiany inaczej

    user_display_name = getattr(current_user, 'name', "")
    user_first_name = getattr(current_user, 'first_name', "")
    user_last_name = getattr(current_user, 'last_name', "")
    final_first_name = user_first_name
    final_last_name = user_last_name

    if not final_first_name and not final_last_name and user_display_name:
        name_parts = user_display_name.strip().split(" ", 1)
        final_first_name = name_parts[0]
        if len(name_parts) > 1: final_last_name = name_parts[1]

    try:
        order = PaymentOrder.objects.create(
            user=current_user,  # Teraz używamy ręcznie pobranego użytkownika
            amount=amount,
            description=description,
            currency='PLN',
            status=PaymentOrder.Status.PENDING,
            buyer_email=current_user.email,
            buyer_first_name=final_first_name,
            buyer_last_name=final_last_name,
        )
        print(f"PAYMENTS_VIEW_INFO: Created DB Order. ext_order_id: {order.ext_order_id}, User: {current_user.email}")
    except Exception as e:
        print(f"PAYMENTS_VIEW_ERROR: DB Order creation failed: {str(e)}")
        return JsonResponse({'error': 'Internal server error: Could not create order record.'}, status=500)

    try:
        notify_url_path = reverse('payments:payu_notify_callback')
        continue_url_path = reverse('payments:payment_finish_page')
        base_url_stripped = settings.YOUR_APP_BASE_URL.rstrip('/')
        notify_url = f"{base_url_stripped}{notify_url_path}"
        continue_url = f"{base_url_stripped}{continue_url_path}"
    except Exception as e:
        print(f"PAYMENTS_VIEW_ERROR: Callback URL generation failed. Check URL conf & YOUR_APP_BASE_URL. Error: {e}")
        order.status = PaymentOrder.Status.FAILED
        order.save()
        return JsonResponse({'error': 'Internal server error: Callback URL configuration error.'}, status=500)

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    customer_ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
    if not customer_ip:
        customer_ip = "127.0.0.1"
        print("PAYMENTS_VIEW_WARNING: Customer IP not found. Using fallback '127.0.0.1'.")

    payu_payload = {
        "notifyUrl": notify_url, "continueUrl": continue_url, "customerIp": customer_ip,
        "merchantPosId": settings.PAYU_MERCHANT_POS_ID, "description": order.description,
        "currencyCode": order.currency, "totalAmount": str(order.amount),
        "extOrderId": order.ext_order_id,
        "buyer": {
            "email": order.buyer_email or current_user.email,
            "firstName": order.buyer_first_name or "Klient",
            "lastName": order.buyer_last_name or "PayU",
            "language": "pl"
        },
        "products": [{"name": order.description, "unitPrice": str(order.amount), "quantity": "1"}],
    }

    payu_response_data = create_payu_order_api_call(payu_payload)

    if not payu_response_data or 'error' in payu_response_data or not payu_response_data.get('redirectUri'):
        error_detail = "Unknown error from PayU service."
        if payu_response_data and 'error' in payu_response_data:
            error_detail = payu_response_data.get('details', payu_response_data['error'])
        elif payu_response_data and not payu_response_data.get('redirectUri'):
            error_detail = "PayU did not return a redirectUri."
            print(f"PAYMENTS_VIEW_ERROR: PayU response missing redirectUri. Response: {payu_response_data}")
        else:
            print(f"PAYMENTS_VIEW_ERROR: Empty/invalid response from PayU service: {payu_response_data}")

        order.status = PaymentOrder.Status.FAILED
        order.save()
        return JsonResponse({'error': 'Failed to initiate payment with PayU.', 'details': error_detail}, status=502)

    order.payu_order_id = payu_response_data.get('orderId')
    order.redirect_uri_payu = payu_response_data.get('redirectUri')
    order.save()

    print(
        f"PAYMENTS_VIEW_INFO: Initiated payment with PayU. PayU Order ID: {order.payu_order_id}. User: {current_user.email}. Redirecting.")

    return JsonResponse({
        'message': 'Payment initiated. Redirecting to PayU...',
        'redirectUri': order.redirect_uri_payu,
        'internalOrderId': str(order.id),
        'payuOrderId': order.payu_order_id
    }, status=200)


# --- PayU IPN (Instant Payment Notification) Receiver ---
@csrf_exempt
@require_POST
def payu_notification_receiver_view(request):
    # ... (kod tego widoku pozostaje taki sam jak w poprzedniej pełnej wersji) ...
    # ... (cała logika weryfikacji podpisu, aktualizacji statusu i logiki biznesowej) ...
    print("PAYMENTS_VIEW_INFO: Received a notification from PayU.")
    raw_notification_body = request.body
    signature_header = request.headers.get('OpenPayU-Signature')

    if not signature_header:
        print("PAYMENTS_VIEW_ERROR: PayU notification missing 'OpenPayU-Signature' header.")
        return HttpResponseBadRequest("Missing signature header.")

    received_signature_value = None
    for part in signature_header.split(';'):
        if part.strip().startswith('signature='):
            received_signature_value = part.split('=', 1)[1].strip()
            break

    if not received_signature_value:
        print("PAYMENTS_VIEW_ERROR: Could not extract signature from 'OpenPayU-Signature' header.")
        return HttpResponseBadRequest("Malformed signature header.")

    payu_signature_key = settings.PAYU_SIGNATURE_KEY
    if not payu_signature_key:
        print("PAYMENTS_VIEW_CRITICAL: PAYU_SIGNATURE_KEY not configured. Cannot verify notification.")
        return HttpResponseServerError("Internal server configuration error for signature key.")

    concatenated_value = raw_notification_body + payu_signature_key.encode('utf-8')
    expected_signature = hashlib.sha256(concatenated_value).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature_value):
        print(
            f"PAYMENTS_VIEW_ERROR: Invalid PayU notification signature. Expected: {expected_signature}, Received: {received_signature_value}")
        return HttpResponseBadRequest("Invalid signature.")

    print("PAYMENTS_VIEW_INFO: PayU notification signature verified successfully.")

    try:
        notification_data = json.loads(raw_notification_body.decode('utf-8'))
    except json.JSONDecodeError as e:
        print(
            f"PAYMENTS_VIEW_ERROR: JSONDecodeError from PayU notification. Error: {e}. Body snippet: {raw_notification_body.decode('utf-8')[:200]}")
        return HttpResponseBadRequest("Invalid JSON payload in notification.")

    order_info = notification_data.get('order')
    if not order_info:
        print("PAYMENTS_VIEW_ERROR: 'order' object missing in PayU notification.")
        return HttpResponseBadRequest("Missing 'order' data in notification.")

    payu_order_id = order_info.get('orderId')
    ext_order_id = order_info.get('extOrderId')
    payu_status = order_info.get('status')

    print(
        f"PAYMENTS_VIEW_INFO: Processing IPN for extOrderId: {ext_order_id}, PayU Order ID: {payu_order_id}, PayU Status: {payu_status}")

    order_to_update = None
    if ext_order_id:
        try:
            order_to_update = PaymentOrder.objects.get(ext_order_id=ext_order_id)
        except PaymentOrder.DoesNotExist:
            if payu_order_id:
                try:
                    order_to_update = PaymentOrder.objects.get(payu_order_id=payu_order_id)
                except PaymentOrder.DoesNotExist:
                    print(
                        f"PAYMENTS_VIEW_ERROR: Order not found by ext_order_id '{ext_order_id}' or payu_order_id '{payu_order_id}'.")
                    return HttpResponse("Order not found, acknowledged.", status=200)
    elif payu_order_id:
        try:
            order_to_update = PaymentOrder.objects.get(payu_order_id=payu_order_id)
        except PaymentOrder.DoesNotExist:
            print(f"PAYMENTS_VIEW_ERROR: Order not found by payu_order_id '{payu_order_id}' (extOrderId missing).")
            return HttpResponse("Order not found, acknowledged.", status=200)
    else:
        print("PAYMENTS_VIEW_ERROR: Both extOrderId and orderId missing in notification.")
        return HttpResponseBadRequest("Missing order identifiers in notification.")

    if not order_to_update:
        print("PAYMENTS_VIEW_ERROR: Failed to identify order to update from IPN after checks.")
        return HttpResponse("Order identification failed, acknowledged.", status=200)

    previous_status = order_to_update.status

    if payu_status == 'COMPLETED':
        order_to_update.status = PaymentOrder.Status.COMPLETED
        print(f"PAYMENTS_VIEW_INFO: Order {order_to_update.ext_order_id} status set to COMPLETED.")

        if order_to_update.user:
            user_to_update = order_to_update.user
            purchased_item_description = order_to_update.description
            print(
                f"  Processing COMPLETED payment for user: {user_to_update.email}, item: '{purchased_item_description}'")
            if hasattr(user_to_update, 'active_profile_frame_name'):
                try:
                    user_to_update.active_profile_frame_name = purchased_item_description
                    user_to_update.save(update_fields=['active_profile_frame_name'])
                    print(
                        f"  SUCCESS: User {user_to_update.email} profile updated with frame: '{purchased_item_description}'.")
                except Exception as e_user_update:
                    print(
                        f"  ERROR: Could not update user profile for {user_to_update.email} with frame. Error: {e_user_update}")
            else:
                print(
                    f"  WARNING: User model for {user_to_update.email} does not have 'active_profile_frame_name' attribute.")
        else:
            print(
                f"  WARNING: PaymentOrder {order_to_update.ext_order_id} is COMPLETED but has no associated user to update.")

    elif payu_status == 'CANCELED':
        order_to_update.status = PaymentOrder.Status.CANCELED
        print(f"PAYMENTS_VIEW_INFO: Order {order_to_update.ext_order_id} status set to CANCELED.")
    elif payu_status in ['PENDING', 'WAITING_FOR_CONFIRMATION']:
        if order_to_update.status != PaymentOrder.Status.COMPLETED:
            order_to_update.status = PaymentOrder.Status.PROCESSING
        print(f"PAYMENTS_VIEW_INFO: Order {order_to_update.ext_order_id} status is PROCESSING (PayU: {payu_status}).")
    else:
        print(
            f"PAYMENTS_VIEW_WARNING: Unmapped PayU status '{payu_status}' for order {order_to_update.ext_order_id}. Considering it FAILED if not already finalized.")
        if order_to_update.status not in [PaymentOrder.Status.COMPLETED, PaymentOrder.Status.CANCELED]:
            order_to_update.status = PaymentOrder.Status.FAILED

    if not order_to_update.payu_order_id and payu_order_id:
        order_to_update.payu_order_id = payu_order_id

    if previous_status != order_to_update.status or \
            (
                    order_to_update.payu_order_id is None and payu_order_id is not None and order_to_update.payu_order_id != payu_order_id):
        order_to_update.save()
        print(
            f"PAYMENTS_VIEW_INFO: Saved changes for order {order_to_update.ext_order_id}. New status: {order_to_update.status}")
    else:
        print(
            f"PAYMENTS_VIEW_INFO: No status/PayU ID change requiring save for order {order_to_update.ext_order_id}. Current status: {order_to_update.status}")

    return HttpResponse("Notification processed.", status=200)


# --- Payment Finish Page View (continueUrl target) ---
def payment_finish_page_view(request):
    """
    View for the page where the user is redirected after the payment process
    on PayU's site (this is the `continueUrl`).
    Displays a status message to the user.
    """
    payu_error_code = request.GET.get('error')
    context = {
        'page_title': "Status Płatności",
        'message': "Dziękujemy! Twoja płatność jest przetwarzana. Otrzymasz potwierdzenie o jej statusie niebawem.",
        'is_error': False,
        'FRONTEND_URL': settings.FRONTEND_URL
    }

    if payu_error_code:
        context[
            'message'] = f"Wystąpił błąd podczas procesu płatności po stronie PayU (kod błędu: {payu_error_code}). Jeśli środki zostały pobrane, prosimy o kontakt z obsługą."
        context['is_error'] = True
        print(f"PAYMENTS_VIEW_INFO: User redirected to finish page with PayU error code: {payu_error_code}")
    else:
        print(f"PAYMENTS_VIEW_INFO: User redirected to finish page. No immediate PayU error in URL.")

    return render(request, 'payments/payments/payment_finish.html', context)