# payments/urls.py
from django.urls import path

from . import views  # Import views from the current application

# Define the application namespace.
# This allows using namespaced URLs like 'payments:initiate_payment' in `reverse()`.
app_name = "payments"

urlpatterns = [
    # URL for initiating a payment.
    # Example: if included in main urls as 'api/payments/', full path would be '/api/payments/initiate/'
    path("initiate/", views.initiate_payment_view, name="initiate_payment_api"),
    # Placeholder URL for PayU notification callback (IPN).
    # This URL will be provided to PayU in the `notifyUrl` field.
    # PayU will send POST requests to this endpoint with transaction status updates.
    # Example: '/api/payments/notify/callback/'
    path(
        "notify/callback/",
        views.payu_notification_receiver_view,
        name="payu_notify_callback",
    ),  # Placeholder view
    # Placeholder URL for the page the user is redirected to after completing/canceling payment on PayU.
    # This URL will be provided to PayU in the `continueUrl` field.
    # Example: '/payments/finish/' (could be a frontend route or a Django-rendered page)
    path(
        "finish/", views.payment_finish_page_view, name="payment_finish_page"
    ),  # Placeholder view
]
