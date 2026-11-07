import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SubscriptionPlan(models.Model):
    """
    Catalog of Kalphora Equity research subscription offerings.
    """
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly (30 Days)'),
        ('quarterly', 'Quarterly (90 Days)'),
        ('semi_annual', 'Semi-Annual (180 Days)'),
        ('annual', 'Annual (365 Days)'),
    )

    code = models.CharField(max_length=64, unique=True, help_text=_("Unique identifier, e.g. SWING_PRO_QUARTERLY"))
    name = models.CharField(max_length=150, help_text=_("Public plan title, e.g. Momentum & Swing Advisory"))
    tagline = models.CharField(max_length=255, blank=True, default="", help_text=_("Short value proposition"))
    price_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    original_price_inr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text=_("Strikethrough price for discount display"))
    duration_days = models.PositiveIntegerField(default=30)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    features = models.JSONField(default=list, blank=True, help_text=_("List of bullet points included in this plan"))
    badge_text = models.CharField(max_length=64, blank=True, default="", help_text=_("Badge like 'Most Popular' or 'SEBI Audited'"))
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'price_inr']
        verbose_name = _('Subscription Plan')
        verbose_name_plural = _('Subscription Plans')

    def __str__(self):
        return f"{self.name} (₹{self.price_inr:,.0f} / {self.get_billing_cycle_display()})"

    @property
    def discount_percent(self):
        if self.original_price_inr and self.original_price_inr > self.price_inr:
            pct = ((self.original_price_inr - self.price_inr) / self.original_price_inr) * 100
            return int(round(pct))
        return 0


class UserSubscription(models.Model):
    """
    Tracks client subscription state, expiration dates, and access privileges.
    """
    STATUS_CHOICES = (
        ('active', 'Active (Paid)'),
        ('trial', 'Complimentary Trial'),
        ('payment_pending', 'Payment Pending'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled by User/Admin'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='user_subscriptions')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='payment_pending')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(help_text=_("Access expiration timestamp"))
    auto_renew = models.BooleanField(default=False)
    
    # Razorpay Transaction Tracking
    razorpay_order_id = models.CharField(max_length=128, blank=True, default="")
    razorpay_payment_id = models.CharField(max_length=128, blank=True, default="")
    razorpay_signature = models.CharField(max_length=256, blank=True, default="")
    invoice_number = models.CharField(max_length=64, blank=True, default="", unique=True, null=True)

    admin_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('User Subscription')
        verbose_name_plural = _('User Subscriptions')

    def __str__(self):
        return f"{self.user.get_display_name()} — {self.plan.name} ({self.status.upper()})"

    @property
    def is_currently_valid(self):
        """Returns True only if status is active/trial and end_date has not passed."""
        if self.status in ('active', 'trial'):
            return self.end_date >= timezone.now()
        return False

    @property
    def days_remaining(self):
        if not self.is_currently_valid:
            return 0
        diff = self.end_date - timezone.now()
        return max(0, diff.days)


class PaymentTransaction(models.Model):
    """
    Audit log of all gateway payment attempts and webhook verifications.
    """
    STATUS_CHOICES = (
        ('created', 'Order Created'),
        ('captured', 'Payment Captured / Verified'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_transactions')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    order_id = models.CharField(max_length=128, db_index=True)
    payment_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    signature = models.CharField(max_length=256, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='INR')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='created')
    gateway_response = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=128, blank=True, default="")
    error_description = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')

    def __str__(self):
        return f"Order #{self.order_id} - ₹{self.amount} ({self.status})"
