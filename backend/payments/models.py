# payments/models.py
from django.db import models
from django.conf import settings  # For referencing the AUTH_USER_MODEL
import uuid  # For generating unique order IDs


class PaymentOrder(models.Model):
    # Enum for payment statuses.
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'  # Order created, awaiting payment.
        PROCESSING = 'PROCESSING', 'Processing'  # Payment in progress with PayU (e.g., WAITING_FOR_CONFIRMATION).
        COMPLETED = 'COMPLETED', 'Completed'  # Payment successfully processed and confirmed.
        CANCELED = 'CANCELED', 'Canceled'  # Payment canceled by user or system.
        FAILED = 'FAILED', 'Failed'  # Payment failed due to technical reasons or rejection.

    # --- Primary and External Identifiers ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Internal unique ID (UUID).
    ext_order_id = models.CharField(max_length=100, unique=True,
                                    blank=True)  # Unique order ID sent to PayU; auto-set in save() if blank.
    payu_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)  # Order ID returned by PayU.

    # --- Financial Details and Status ---
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)  # Current payment status.
    amount = models.PositiveIntegerField()  # Order amount in the smallest currency unit (e.g., grosze for PLN).
    currency = models.CharField(max_length=3, default='PLN')  # Transaction currency code (e.g., PLN).
    description = models.CharField(
        max_length=255)  # Brief order description for PayU (e.g., "Zakup ramki profilowej 'NazwaRamki'").

    # --- Association with User Model ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # References 'accounts.User' as defined in your settings.
        on_delete=models.SET_NULL,
        # If the user is deleted, set this field to NULL. Consider models.PROTECT or models.CASCADE based on your needs.
        null=True,  # Allows this field to be NULL in the database.
        blank=True,  # Allows this field to be blank in forms (though for logged-in users, it should be set).
        related_name='payment_orders'  # Name to access payment orders from a user instance (user.payment_orders.all()).
    )

    # --- Buyer Information (can be pre-filled from user model or provided separately) ---
    buyer_email = models.EmailField(blank=True, null=True)  # Could be pre-filled from user.email
    buyer_first_name = models.CharField(max_length=100, blank=True,
                                        null=True)  # Could be pre-filled from user.first_name
    buyer_last_name = models.CharField(max_length=100, blank=True, null=True)  # Could be pre-filled from user.last_name

    # --- PayU Process Related Data ---
    redirect_uri_payu = models.URLField(max_length=500, blank=True, null=True)  # Redirect URL to PayU payment gateway.

    # --- Timestamps (Automatically Managed by Django) ---
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp of order record creation.
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp of last order record modification.

    class Meta:
        ordering = ['-created_at']  # Default ordering: newest first.
        verbose_name = "Payment Order"  # Singular display name in Django admin.
        verbose_name_plural = "Payment Orders"  # Plural display name in Django admin.

    def __str__(self):
        # String representation of the model instance.
        amount_readable = f"{self.amount / 100:.2f}"
        user_info = f" by User ID: {self.user_id}" if self.user_id else ""
        return f"Order {self.ext_order_id or self.id} ({self.get_status_display()}) - {amount_readable} {self.currency}{user_info}"

    def save(self, *args, **kwargs):
        # Overridden save method.
        # Automatically sets `ext_order_id` from the `id` (UUID) if not provided.
        if not self.ext_order_id:
            self.ext_order_id = str(self.id)
        super().save(*args, **kwargs)