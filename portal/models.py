import uuid
import hashlib
import json
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class StockRecommendation(models.Model):
    """
    Core research recommendation model.
    Free users see teaser metrics (Potential % and Horizon);
    Premium subscribers see complete parameters (Ticker, Action, Entry, Target, Stop-Loss).
    """
    HORIZON_CHOICES = (
        ('intraday', 'Intraday'),
        ('short_term', 'Short Term / Swing (1-4 Weeks)'),
        ('mid_long_term', 'Mid/Long Term (3-12 Months)'),
        ('futures', 'Futures'),
        ('options', 'Options Strategies'),
    )

    ACTION_CHOICES = (
        ('BUY', 'BUY'),
        ('ACCUMULATE', 'ACCUMULATE ON DIPS'),
        ('HOLD', 'HOLD'),
        ('BOOK_PARTIAL', 'BOOK PARTIAL PROFIT'),
        ('EXIT', 'EXIT / SELL'),
    )

    STATUS_CHOICES = (
        ('open', 'Open Trade'),
        ('target_hit', 'Target 1 Achieved'),
        ('target_2_hit', 'Target 2 Achieved'),
        ('sl_hit', 'Stop-Loss Triggered'),
        ('closed', 'Closed & Realized'),
        ('cancelled', 'Cancelled by Analyst'),
    )

    SECTOR_CHOICES = (
        ('Banking & Financials', 'Banking & Financials'),
        ('IT & Technology', 'IT & Technology'),
        ('Auto & Ancillaries', 'Auto & Ancillaries'),
        ('Cement & Building Materials', 'Cement & Building Materials'),
        ('Pharmaceuticals & Healthcare', 'Pharmaceuticals & Healthcare'),
        ('Metals & Mining', 'Metals & Mining'),
        ('Energy, Oil & Gas', 'Energy, Oil & Gas'),
        ('Defence & Aerospace', 'Defence & Aerospace'),
        ('FMCG & Consumption', 'FMCG & Consumption'),
        ('Infrastructure & Capital Goods', 'Infrastructure & Capital Goods'),
        ('Chemicals & Agrochemicals', 'Chemicals & Agrochemicals'),
        ('Diversified Conglomerates', 'Diversified Conglomerates'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticker = models.CharField(max_length=32, db_index=True, help_text=_("Stock Symbol, e.g. SHREECEM, RELIANCE"))
    company_name = models.CharField(max_length=150, help_text=_("Full Company Name, e.g. Shree Cement Limited"))
    exchange = models.CharField(max_length=8, default='NSE')
    sector = models.CharField(max_length=64, choices=SECTOR_CHOICES, default='Banking & Financials')
    horizon = models.CharField(max_length=20, choices=HORIZON_CHOICES, default='short_term')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default='BUY')
    
    # Pricing Parameters
    entry_min_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Lower range of recommended entry"))
    entry_max_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Upper range of recommended entry"))
    target_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Primary target price"))
    secondary_target = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Hard stop-loss level"))
    trailing_stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Teaser Metric for Free Users (Screenshot 2: "POTENTIAL LEFT: 9.45%")
    potential_upside_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text=_("Estimated upside %"))
    risk_reward_ratio = models.CharField(max_length=16, default='1:2.5', help_text=_("e.g. 1:2.5"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Analyst Research Rationale
    thesis_summary = models.TextField(help_text=_("Concise summary of rationale (visible to all premium)"))
    full_research_notes = models.TextField(blank=True, default="", help_text=_("Deep forensic balance sheet, technical breakout & catalyst details"))
    
    # Timestamps & Closure
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    exit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    realized_gain_percent = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # SEBI Regulation 25 Compliance Audit Hash
    sha256_hash = models.CharField(max_length=64, blank=True, default="", help_text=_("Immutable SHA-256 snapshot"))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='recommendations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = _('Stock Recommendation')
        verbose_name_plural = _('Stock Recommendations')

    def __str__(self):
        return f"[{self.action}] {self.ticker} ({self.get_horizon_display()}) — Status: {self.get_status_display()}"

    def calculate_sha256(self):
        payload = f"{self.ticker}|{self.action}|{self.entry_min_price}|{self.entry_max_price}|{self.target_price}|{self.stop_loss}|{self.published_at.isoformat()}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        # Compute upside percentage automatically if not manually set
        if not self.potential_upside_percent and self.entry_max_price and self.target_price and self.target_price > self.entry_max_price:
            self.potential_upside_percent = round(((self.target_price - self.entry_max_price) / self.entry_max_price) * 100, 2)
            
        self.sha256_hash = self.calculate_sha256()
        super().save(*args, **kwargs)
        
        # Log to SEBI Regulation 25 Audit Engine
        action_type = 'published' if is_new else 'updated'
        SEBIComplianceAuditLog.log_snapshot(self, action_type=action_type)


class RecommendationUpdate(models.Model):
    """
    Live intra-trade updates (e.g., Trailing SL raised, Target 1 Hit, Book 50% Profit).
    """
    UPDATE_TYPE_CHOICES = (
        ('trailing_sl', 'Trailing Stop-Loss Updated'),
        ('partial_profit', 'Partial Profit Booking Recommended'),
        ('target_achieved', 'Target Price Milestone Achieved'),
        ('target_raised', 'Target Price Revised Upward'),
        ('exit_now', 'Urgent Exit Call'),
        ('commentary', 'Market & Earnings Commentary'),
    )

    id = models.BigAutoField(primary_key=True)
    recommendation = models.ForeignKey(StockRecommendation, on_delete=models.CASCADE, related_name='updates')
    update_type = models.CharField(max_length=32, choices=UPDATE_TYPE_CHOICES, default='trailing_sl')
    headline = models.CharField(max_length=200)
    message = models.TextField()
    new_stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Recommendation Update')
        verbose_name_plural = _('Recommendation Updates')

    def __str__(self):
        return f"{self.recommendation.ticker} Update: {self.headline} ({self.timestamp.strftime('%d %b %H:%M')})"


class SEBIComplianceAuditLog(models.Model):
    """
    Regulation 25 (SEBI Research Analyst Regulations, 2014) Mandatory Audit Engine.
    Retains immutable, tamper-evident SHA-256 historical snapshots of every call for 5 years.
    """
    id = models.BigAutoField(primary_key=True)
    recommendation = models.ForeignKey(StockRecommendation, on_delete=models.CASCADE, related_name='compliance_logs')
    action_type = models.CharField(max_length=32)
    snapshot_payload = models.JSONField(help_text=_("Full state payload at time of event"))
    sha256_checksum = models.CharField(max_length=64)
    logged_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-logged_at']
        verbose_name = _('SEBI Regulation 25 Audit Log')
        verbose_name_plural = _('SEBI Regulation 25 Audit Logs')

    def __str__(self):
        return f"SEBI Audit #{self.id} - {self.action_type.upper()} on {self.logged_at.strftime('%Y-%m-%d %H:%M:%S')}"

    @classmethod
    def log_snapshot(cls, recommendation, action_type='published'):
        payload = {
            'ticker': recommendation.ticker,
            'company_name': recommendation.company_name,
            'action': recommendation.action,
            'horizon': recommendation.horizon,
            'entry_range': [str(recommendation.entry_min_price), str(recommendation.entry_max_price)],
            'target_price': str(recommendation.target_price),
            'stop_loss': str(recommendation.stop_loss),
            'potential_upside_percent': str(recommendation.potential_upside_percent),
            'status': recommendation.status,
            'published_at': recommendation.published_at.isoformat() if recommendation.published_at else None,
            'analyst_id': recommendation.created_by_id if recommendation.created_by else None,
        }
        checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
        cls.objects.create(
            recommendation=recommendation,
            action_type=action_type,
            snapshot_payload=payload,
            sha256_checksum=checksum,
            logged_at=timezone.now()
        )


class ClientWatchlist(models.Model):
    """
    Registered client's personal stock watchlist.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist_items')
    ticker = models.CharField(max_length=32, db_index=True)
    company_name = models.CharField(max_length=150)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'ticker')
        ordering = ['-created_at']
        verbose_name = _('Client Watchlist Item')
        verbose_name_plural = _('Client Watchlist Items')

    def __str__(self):
        return f"{self.user.get_display_name()} ➔ {self.ticker}"


# ==============================================================================
# DYNAMIC PORTAL CONFIGURATION & CLIENT PERMISSION OVERRIDE SYSTEM
# ==============================================================================

class PortalSectionConfig(models.Model):
    """
    Administrator-governed configuration for Client Portal modules/tabs.
    Allows enabling/disabling sections, setting titles, requiring premium,
    and ordering without modifying code or redeploying.
    """
    section_key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Unique identifier, e.g. 'market', 'calls', 'screener', 'sectors', 'corporate_actions', 'vault', 'watchlist'")
    )
    title = models.CharField(max_length=100, help_text=_("Display label on navigation tab"))
    subtitle = models.CharField(max_length=255, blank=True, default="", help_text=_("Short contextual description"))
    url_name = models.CharField(max_length=100, default='portal:dashboard', help_text=_("Django URL pattern name"))
    icon_name = models.CharField(max_length=50, default='grid', help_text=_("Icon name or emoji symbol"))
    is_enabled_globally = models.BooleanField(
        default=True,
        help_text=_("Master switch: If unchecked, this section is hidden globally from all users unless explicitly overridden.")
    )
    requires_premium = models.BooleanField(
        default=False,
        help_text=_("If checked, only active paying subscribers (or VIP overrides) can access this section.")
    )
    is_visible_in_nav = models.BooleanField(
        default=True,
        help_text=_("Whether this section renders as a tab in the main portal navigation.")
    )
    display_order = models.PositiveIntegerField(default=0, help_text=_("Tab order (lowest appears first)"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = _('Portal Section Configuration')
        verbose_name_plural = _('Portal Section Configurations')

    def __str__(self):
        status = "🟢 Enabled" if self.is_enabled_globally else "🔴 Disabled"
        tier = "🔒 Premium" if self.requires_premium else "🔓 Free"
        return f"{self.title} ({self.section_key}) — {status} | {tier}"


class ClientPortalAccessOverride(models.Model):
    """
    Enables the Administrator to customize access on an INDIVIDUAL CLIENT basis.
    E.g., Give Client A VIP access to 'Premium Calls' or 'Research Vault' even without
    a paid subscription, or restrict Client B from certain modules.
    Enforced strictly server-side in portal dispatch and views.
    """
    ACCESS_STATUS_CHOICES = (
        ('DEFAULT', 'Default (Follow Global & Plan Tier Rules)'),
        ('FORCE_ENABLED', 'VIP Granted (Force Enabled even if free)'),
        ('FORCE_DISABLED', 'Revoked / Restricted (Force Disabled for this client)'),
    )

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='portal_access_overrides'
    )
    section = models.ForeignKey(
        PortalSectionConfig,
        on_delete=models.CASCADE,
        related_name='client_overrides'
    )
    access_status = models.CharField(
        max_length=20,
        choices=ACCESS_STATUS_CHOICES,
        default='DEFAULT',
        help_text=_("Determines whether this client has standard, forced access (VIP), or revoked access.")
    )
    custom_badge = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text=_("Optional badge displayed next to tab, e.g. 'VIP', 'Complimentary', 'Beta'")
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text=_("Internal administrative reason for this override (compliance documentation).")
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Optional expiry timestamp for temporary trial or courtesy access.")
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='overrides_granted'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('client', 'section')
        ordering = ['client', 'section__display_order']
        verbose_name = _('Individual Client Access Override')
        verbose_name_plural = _('Individual Client Access Overrides')

    def __str__(self):
        return f"{self.client.get_display_name()} ➔ {self.section.title}: {self.get_access_status_display()}"

    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False


class PortalWidgetConfig(models.Model):
    """
    Dynamic widgets, banners, and sidebar cards manageable via Admin.
    Allows changing promotion banners, pricing teasers, or announcements dynamically.
    """
    WIDGET_TYPE_CHOICES = (
        ('sidebar_card', 'Right Sidebar Card / Promo'),
        ('dashboard_banner', 'Top Dashboard Alert Banner'),
        ('inline_notice', 'Inline Module Card'),
    )

    TARGET_TIER_CHOICES = (
        ('all', 'All Clients'),
        ('free_only', 'Free Tier Only (Upsell Target)'),
        ('premium_only', 'Premium Tier Only (Exclusive)'),
    )

    widget_key = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=150)
    widget_type = models.CharField(max_length=32, choices=WIDGET_TYPE_CHOICES, default='sidebar_card')
    target_tier = models.CharField(max_length=20, choices=TARGET_TIER_CHOICES, default='all')
    content_html = models.TextField(blank=True, default="", help_text=_("Rich HTML content or copy for the card"))
    cta_text = models.CharField(max_length=100, blank=True, default="", help_text=_("e.g. Upgrade Now →"))
    cta_url = models.CharField(max_length=255, blank=True, default="", help_text=_("Target link or reverse URL"))
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = _('Portal Widget Configuration')
        verbose_name_plural = _('Portal Widget Configurations')

    def __str__(self):
        status = "🟢 Active" if self.is_active else "🔴 Inactive"
        return f"[{self.get_widget_type_display()}] {self.title} — {status} ({self.get_target_tier_display()})"


class PortalAnnouncement(models.Model):
    """
    Flash announcements, SEBI advisories, and market alerts broadcast to clients.
    Can target all users, free only, premium only, or specific clients.
    """
    ANNOUNCEMENT_TYPE_CHOICES = (
        ('info', 'ℹ️ Market Advisory / Informational'),
        ('warning', '⚠️ Volatility & Risk Warning'),
        ('success', '🎯 Target Achieved / New Research Call'),
        ('urgent', '🚨 Urgent / Action Required'),
    )

    TARGET_TIER_CHOICES = (
        ('all', 'All Clients'),
        ('free_only', 'Free Clients Only'),
        ('premium_only', 'Premium Clients Only'),
        ('specific_clients', 'Specific Selected Clients Only'),
    )

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200)
    message = models.TextField(help_text=_("Announcement text. Supports safe HTML or plain text."))
    announcement_type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPE_CHOICES, default='info')
    target_tier = models.CharField(max_length=20, choices=TARGET_TIER_CHOICES, default='all')
    specific_clients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='portal_announcements',
        help_text=_("Select specific clients if 'Specific Selected Clients Only' is chosen.")
    )
    is_active = models.BooleanField(default=True)
    is_dismissible = models.BooleanField(default=True, help_text=_("Can clients close this banner in their session?"))
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, help_text=_("Leave empty for indefinite duration"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Portal Announcement')
        verbose_name_plural = _('Portal Announcements')

    def __str__(self):
        status = "🟢 Active" if self.is_active else "🔴 Inactive"
        return f"{self.get_announcement_type_display()} - {self.title} [{status}]"

    def is_current(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True
