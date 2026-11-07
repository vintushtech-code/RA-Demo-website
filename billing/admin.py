from datetime import timedelta
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import SubscriptionPlan, UserSubscription, PaymentTransaction
from login.models import SecurityAuditLog


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price_inr', 'original_price_inr', 'discount_percent_display', 'duration_days', 'billing_cycle', 'is_active', 'display_order')
    list_editable = ('price_inr', 'is_active', 'display_order')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('name', 'code', 'tagline')
    ordering = ('display_order', 'price_inr')

    @admin.display(description=_("Discount %"))
    def discount_percent_display(self, obj):
        pct = obj.discount_percent
        return f"{pct}% OFF" if pct > 0 else "—"


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status_badge', 'start_date', 'end_date', 'days_remaining_display', 'invoice_number')
    list_filter = ('status', 'plan', 'auto_renew', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__email', 'invoice_number', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('id', 'user', 'plan', 'start_date', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'invoice_number', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    actions = ['grant_courtesy_extension_7d', 'terminate_subscription_action']

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            'active': ('rgba(16, 185, 129, 0.2)', '#10B981', '⭐ ACTIVE'),
            'trial': ('rgba(212, 175, 55, 0.2)', '#D4AF37', '🎁 TRIAL'),
            'payment_pending': ('rgba(234, 179, 8, 0.2)', '#FBBF24', '⏳ PENDING'),
            'expired': ('rgba(148, 163, 184, 0.2)', '#94A3B8', 'EXPIRED'),
            'cancelled': ('rgba(239, 68, 68, 0.2)', '#EF4444', 'CANCELLED'),
        }
        bg, fg, label = colors.get(obj.status, ('rgba(148, 163, 184, 0.2)', '#94A3B8', obj.status))
        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">{}</span>',
            bg, fg, label
        )

    @admin.display(description=_("Days Remaining"))
    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days > 0:
            return format_html('<span style="color: #10B981; font-weight: 700;">{} days</span>', days)
        return format_html('<span style="color: #EF4444;">0 days (Expired)</span>')

    @admin.action(description=_("🛡️ Grant Authorized Complimentary Extension (+7 Days)"))
    def grant_courtesy_extension_7d(self, request, queryset):
        count = 0
        for sub in queryset:
            base_date = max(sub.end_date, timezone.now())
            sub.end_date = base_date + timedelta(days=7)
            sub.status = 'active'
            sub.save(update_fields=['end_date', 'status'])
            count += 1
            SecurityAuditLog.log(
                'permission_override',
                actor=request.user,
                target=sub.user,
                details={'action': 'ADMIN_EXTENSION_7D', 'subscription_id': str(sub.id), 'new_end_date': sub.end_date.isoformat()}
            )
        self.message_user(request, f"{count} subscription(s) granted 7-day complimentary extension with audit logging.")

    @admin.action(description=_("🚫 Terminate / Cancel Selected Subscriptions"))
    def terminate_subscription_action(self, request, queryset):
        count = 0
        for sub in queryset:
            sub.status = 'cancelled'
            sub.save(update_fields=['status'])
            count += 1
            SecurityAuditLog.log(
                'permission_override',
                actor=request.user,
                target=sub.user,
                details={'action': 'ADMIN_SUBSCRIPTION_TERMINATED', 'subscription_id': str(sub.id)}
            )
        self.message_user(request, f"{count} subscription(s) terminated.")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """
    Immutable Financial Audit Record.
    Administrators CANNOT tamper with gateway records or flip status without cryptographic verification.
    """
    list_display = ('order_id', 'user', 'amount_display', 'status_badge', 'payment_id', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('order_id', 'payment_id', 'user__username', 'user__email')
    readonly_fields = (
        'id', 'user', 'subscription', 'order_id', 'payment_id', 'signature',
        'amount', 'currency', 'status', 'gateway_response', 'error_code',
        'error_description', 'ip_address', 'created_at'
    )
    ordering = ('-created_at',)

    @admin.display(description=_("Amount"))
    def amount_display(self, obj):
        return f"₹{obj.amount:,.2f}"

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            'captured': ('rgba(16, 185, 129, 0.2)', '#10B981', '✔ CAPTURED / PAID'),
            'created': ('rgba(234, 179, 8, 0.2)', '#FBBF24', '⏳ ORDER CREATED'),
            'failed': ('rgba(239, 68, 68, 0.2)', '#EF4444', '✖ FAILED'),
            'refunded': ('rgba(148, 163, 184, 0.2)', '#94A3B8', '↩ REFUNDED'),
        }
        bg, fg, label = colors.get(obj.status, ('rgba(148, 163, 184, 0.2)', '#94A3B8', obj.status))
        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">{}</span>',
            bg, fg, label
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Sensitive payment records cannot be deleted via admin
        return False
