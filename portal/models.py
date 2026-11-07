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
