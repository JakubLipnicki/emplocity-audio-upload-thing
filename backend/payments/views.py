# backend/payments/views.py
import json
import hashlib
import hmac

from django.http import HttpResponseBadRequest, HttpResponseServerError, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from django.shortcuts import render, get_object_or_404  # Dodano get_object_or_404

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.authentication import JWTAuthentication
from .models import PaymentOrder
from .payu_service import create_payu_order_api_call


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def initiate_payment_view(request):
    # ... (kod tego widoku pozostaje bez zmian, tak jak w ostatniej pełnej wersji) ...
    current_user = request.user
    try:
        data = request.data
        amount_raw = data.get('amount')
        description = data.get('description')
        if amount_raw is None:
            return Response({'error': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = int(amount_raw)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount format. Must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Invalid amount (must be positive integer in grosze).'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not description:
            return Response({'error': 'Description is required.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"PAYMENTS_VIEW_ERROR: Error processing request data in initiate_payment_view: {str(e)}")
        return Response({'error': f'Error processing request data: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    user_display_name = getattr(current_user, 'name', "")
    user_first_name = getattr(current_user, 'first_name', "")
    user_last_name = getattr(current_user, 'last_name', "")
    final_first_name = user_first_name
    final_last_name = user_last_name
    if not final_first_name and not final_last_name and user_display_name:
        name_parts = user_display_name.strip().split(" ", 1)
        final_first_name = name_parts[0]
        if len(name_parts) > 1:
            final_last_name = name_parts[1]
    try:
        order = PaymentOrder.objects.create(
            user=current_user, amount=amount, description=description, currency='PLN',
            status=PaymentOrder.Status.PENDING, buyer_email=current_user.email,
            buyer_first_name=final_first_name, buyer_last_name=final_last_name,
        )
        print(f"PAYMENTS_VIEW_INFO: Created DB Order. ext_order_id: {order.ext_order_id}, User: {current_user.email}")
    except Exception as e:
        print(f"PAYMENTS_VIEW_ERROR: DB Order creation failed: {str(e)}")
        return Response({'error': 'Internal server error: Could not create order record.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- MODYFIKACJA continueUrl, aby zawierał internal_order_id ---
    try:
        notify_url_path = reverse('payments:payu_notify_callback')
        # Tworzymy bazowy continue_url
        base_continue_url_path = reverse('payments:payment_finish_page')
        base_url_stripped = settings.YOUR_APP_BASE_URL.rstrip('/')
        notify_url = f"{base_url_stripped}{notify_url_path}"
        # Do continue_url dodajemy parametr z naszym wewnętrznym ID zamówienia
        continue_url = f"{base_url_stripped}{base_continue_url_path}?internal_order_id={order.id}"
    except Exception as e:
        print(f"PAYMENTS_VIEW_ERROR: Callback URL generation failed. Check URL conf & YOUR_APP_BASE_URL. Error: {e}")
        order.status = PaymentOrder.Status.FAILED
        order.save()
        return Response({'error': 'Internal server error: Callback URL configuration error.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # --- KONIEC MODYFIKACJI ---

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    customer_ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
    if not customer_ip:
        customer_ip = "127.0.0.1"
        print("PAYMENTS_VIEW_WARNING: Customer IP not found. Using fallback '127.0.0.1'.")
    payu_payload = {
        "notifyUrl": notify_url, "continueUrl": continue_url, "customerIp": customer_ip,
        # Używamy zmodyfikowanego continue_url
        "merchantPosId": settings.PAYU_MERCHANT_POS_ID, "description": order.description,
        "currencyCode": order.currency, "totalAmount": str(order.amount),
        "extOrderId": order.ext_order_id,
        "buyer": {"email": order.buyer_email or current_user.email, "firstName": order.buyer_first_name or "Klient",
                  "lastName": order.buyer_last_name or "PayU", "language": "pl"},
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
        return Response({'error': 'Failed to initiate payment with PayU.', 'details': error_detail},
                        status=status.HTTP_502_BAD_GATEWAY)
    order.payu_order_id = payu_response_data.get('orderId')
    order.redirect_uri_payu = payu_response_data.get('redirectUri')
    order.save()
    print(
        f"PAYMENTS_VIEW_INFO: Initiated payment with PayU. PayU Order ID: {order.payu_order_id}. User: {current_user.email}. Redirecting.")
    return Response({
        'message': 'Payment initiated. Redirecting to PayU...',
        'redirectUri': order.redirect_uri_payu,
        'internalOrderId': str(order.id),
        'payuOrderId': order.payu_order_id
    }, status=status.HTTP_200_OK)


@csrf_exempt
@require_POST
def payu_notification_receiver_view(request):
    # ... (kod tego widoku pozostaje taki sam jak w ostatniej pełnej wersji) ...
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
    payu_order_id_from_ipn = order_info.get('orderId')  # Zmieniono nazwę zmiennej
    ext_order_id = order_info.get('extOrderId')
    payu_status = order_info.get('status')
    print(
        f"PAYMENTS_VIEW_INFO: Processing IPN for extOrderId: {ext_order_id}, PayU Order ID: {payu_order_id_from_ipn}, PayU Status: {payu_status}")
    order_to_update = None
    if ext_order_id:
        try:
            order_to_update = PaymentOrder.objects.get(ext_order_id=ext_order_id)
        except PaymentOrder.DoesNotExist:
            if payu_order_id_from_ipn:
                try:
                    order_to_update = PaymentOrder.objects.get(payu_order_id=payu_order_id_from_ipn)
                except PaymentOrder.DoesNotExist:
                    print(
                        f"PAYMENTS_VIEW_ERROR: Order not found by ext_order_id '{ext_order_id}' or payu_order_id '{payu_order_id_from_ipn}'.")
                    return HttpResponse("Order not found, acknowledged.", status=200)
    elif payu_order_id_from_ipn:
        try:
            order_to_update = PaymentOrder.objects.get(payu_order_id=payu_order_id_from_ipn)
        except PaymentOrder.DoesNotExist:
            print(
                f"PAYMENTS_VIEW_ERROR: Order not found by payu_order_id '{payu_order_id_from_ipn}' (extOrderId missing).")
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
    if not order_to_update.payu_order_id and payu_order_id_from_ipn:  # Używamy payu_order_id_from_ipn
        order_to_update.payu_order_id = payu_order_id_from_ipn
    if previous_status != order_to_update.status or \
            (
                    order_to_update.payu_order_id is None and payu_order_id_from_ipn is not None and order_to_update.payu_order_id != payu_order_id_from_ipn):
        order_to_update.save()
        print(
            f"PAYMENTS_VIEW_INFO: Saved changes for order {order_to_update.ext_order_id}. New status: {order_to_update.status}")
    else:
        print(
            f"PAYMENTS_VIEW_INFO: No status/PayU ID change requiring save for order {order_to_update.ext_order_id}. Current status: {order_to_update.status}")
    return HttpResponse("Notification processed.", status=200)


# --- ZAKTUALIZOWANY WIDOK payment_finish_page_view ---
def payment_finish_page_view(request):
    """
    View for the page where the user is redirected after the payment process
    on PayU's site (this is the `continueUrl`).
    Displays a status message to the user, potentially based on order details.
    """
    payu_error_code = request.GET.get('error')
    internal_order_id_str = request.GET.get('internal_order_id')  # Odczytujemy ID naszego zamówienia

    order = None
    specific_order_message = ""

    if internal_order_id_str:
        try:
            internal_order_id = uuid.UUID(internal_order_id_str)  # Konwersja na UUID
            # Pobierz zamówienie. Jeśli użytkownik jest zalogowany, upewnij się, że to jego zamówienie.
            # Jeśli nie jest zalogowany, a chcesz pokazać szczegóły, to jest ryzyko (ale continueUrl jest trudny do odgadnięcia).
            # Dla bezpieczeństwa, można by wymagać zalogowania, aby zobaczyć szczegóły zamówienia.
            # Na razie zakładamy, że ID jest wystarczające lub użytkownik jest anonimowy/już wylogowany.
            order_query = PaymentOrder.objects.filter(id=internal_order_id)
            if request.user.is_authenticated:  # Jeśli użytkownik jest zalogowany, filtruj po nim
                order_query = order_query.filter(user=request.user)

            order = order_query.first()  # Użyj .first() zamiast .get(), aby uniknąć wyjątku, jeśli nie ma (choć get_object_or_404 by to obsłużył)

            if order:
                if order.status == PaymentOrder.Status.COMPLETED:
                    specific_order_message = f"Płatność za zamówienie '{order.description}' (ID: {order.ext_order_id}) została pomyślnie zakończona."
                elif order.status == PaymentOrder.Status.CANCELED:
                    specific_order_message = f"Płatność za zamówienie '{order.description}' (ID: {order.ext_order_id}) została anulowana."
                elif order.status == PaymentOrder.Status.FAILED:
                    specific_order_message = f"Płatność za zamówienie '{order.description}' (ID: {order.ext_order_id}) nie powiodła się."
                # Dla PENDING lub PROCESSING, domyślny komunikat może być wystarczający.
            else:  # Order not found or doesn't belong to the user
                print(
                    f"PAYMENTS_VIEW_WARNING: User redirected to finish page, but order with ID {internal_order_id_str} not found or access denied.")
                specific_order_message = "Nie można odnaleźć szczegółów Twojego zamówienia."
        except ValueError:  # Jeśli internal_order_id_str nie jest poprawnym UUID
            print(f"PAYMENTS_VIEW_ERROR: Invalid internal_order_id format in GET params: {internal_order_id_str}")
            specific_order_message = "Wystąpił błąd podczas przetwarzania informacji o zamówieniu (niepoprawny identyfikator)."
        except Exception as e:
            print(f"PAYMENTS_VIEW_ERROR: Error fetching order details in finish page: {e}")
            specific_order_message = "Wystąpił błąd podczas pobierania szczegółów zamówienia."

    default_message = "Dziękujemy! Twoja płatność jest przetwarzana. Otrzymasz potwierdzenie o jej statusie niebawem."

    context = {
        'page_title': "Status Płatności",
        'message': specific_order_message or default_message,
        'is_error': False,
        'FRONTEND_URL': settings.FRONTEND_URL,
        'order': order  # Przekazujemy obiekt zamówienia do szablonu (może być None)
    }

    if payu_error_code:
        context[
            'message'] = f"Wystąpił błąd podczas procesu płatności po stronie PayU (kod błędu: {payu_error_code}). {specific_order_message or 'Jeśli środki zostały pobrane, prosimy o kontakt z obsługą.'}"
        context['is_error'] = True
        print(f"PAYMENTS_VIEW_INFO: User redirected to finish page with PayU error code: {payu_error_code}")
    elif order and order.status == PaymentOrder.Status.FAILED:  # Jeśli nasze IPN oznaczyło jako FAILED
        context['is_error'] = True  # Traktuj FAILED jako błąd dla użytkownika
        if not specific_order_message:  # Użyj ogólnego komunikatu o błędzie, jeśli nie ma bardziej szczegółowego
            context[
                'message'] = "Niestety, Twoja płatność nie powiodła się. Spróbuj ponownie lub skontaktuj się z nami."

    print(f"PAYMENTS_VIEW_INFO: Rendering finish page. Context message: {context['message']}")

    return render(request, 'payments/payment_finish.html', context)