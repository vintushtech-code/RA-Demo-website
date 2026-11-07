from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, PaymentTransaction


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price_inr', 'duration_days', 'billing_cycle', 'is_active', 'display_order')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('name', 'code', 'tagline')
    ordering = ('display_order', 'price_inr')


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'is_currently_valid_display', 'invoice_number')
    list_filter = ('status', 'plan', 'auto_renew')
    search_fields = ('user__username', 'user__email', 'invoice_number', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def is_currently_valid_display(self, obj):
        return obj.is_currently_valid
    is_currently_valid_display.boolean = True
    is_currently_valid_display.short_description = "Valid Access"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'amount', 'currency', 'status', 'payment_id', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('order_id', 'payment_id', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
