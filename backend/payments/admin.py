# payments/admin.py
from django.contrib import admin

from .models import PaymentOrder  # Import your PaymentOrder model


@admin.register(PaymentOrder)  # Decorator to register the model with the admin site
class PaymentOrderAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the PaymentOrder model.
    Defines how PaymentOrder records are displayed and managed in the Django admin.
    """

    # Fields to display in the main list view of PaymentOrders.
    list_display = (
        "ext_order_id",
        "payu_order_id",
        "status",
        "amount_display",  # Custom method to display amount formatted as currency.
        "currency",
        "user_email_display",  # Custom method to display user's email.
        "created_at",
        "updated_at",
    )

    # Fields that can be used to filter the list view.
    list_filter = ("status", "currency", "created_at", "updated_at")

    # Fields that can be searched in the list view.
    search_fields = (
        "id__iexact",  # Search by exact UUID (case-insensitive for __iexact, though UUIDs are usually case-sensitive)
        "ext_order_id__iexact",
        "payu_order_id__iexact",
        "user__email__icontains",  # Search by user's email (if user field is linked)
        "user__username__icontains",  # Search by username (if user field is linked)
        "buyer_email__icontains",
        "description__icontains",
    )

    # Fields that should be read-only in the admin edit/add form.
    # These are typically auto-generated or managed by the system.
    readonly_fields = (
        "id",  # Primary key, usually not editable.
        "ext_order_id",  # Auto-generated or set programmatically.
        "payu_order_id",  # Set by PayU integration.
        "redirect_uri_payu",  # Set by PayU integration.
        "created_at",  # Auto-set on creation.
        "updated_at",  # Auto-set on update.
    )

    # Defines the layout of the edit/add form using fieldsets.
    # Organizes fields into logical groups.
    fieldsets = (
        (
            None,
            {  # Main section, no title
                "fields": (
                    "id",
                    "status",
                    "amount",
                    "currency",
                    "user",
                )  # Add 'user' if you have it linked.
            },
        ),
        (
            "PayU Integration Details",
            {
                "fields": (
                    "ext_order_id",
                    "payu_order_id",
                    "redirect_uri_payu",
                    "description",
                )
            },
        ),
        (
            "Buyer Information",
            {  # Information about the person making the payment.
                "fields": ("buyer_email", "buyer_first_name", "buyer_last_name")
            },
        ),
        (
            "Timestamps",
            {  # Auto-managed date and time fields.
                "fields": ("created_at", "updated_at"),
                "classes": (
                    "collapse",
                ),  # Makes this fieldset collapsible in the admin interface.
            },
        ),
    )

    # Custom method to display the amount formatted as currency (e.g., 123.00 PLN).
    def amount_display(self, obj):
        return f"{obj.amount / 100:.2f} {obj.currency}"

    amount_display.short_description = "Amount"  # Column header in the admin list view.
    amount_display.admin_order_field = "amount"  # Allows sorting by the 'amount' field.

    # Custom method to display the user's email if the order is linked to a user.
    def user_email_display(self, obj):
        if obj.user:
            return obj.user.email  # Assumes your AUTH_USER_MODEL has an 'email' field.
        return "-"  # Display a dash if no user is linked.

    user_email_display.short_description = "User Email"
    user_email_display.admin_order_field = (
        "user__email"  # Allows sorting by user's email.
    )
