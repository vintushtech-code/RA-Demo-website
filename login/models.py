"""
Custom User Model & Database Definitions
=========================================

Extends Django's AbstractUser to provide unique email authentication,
social OAuth provider tracking, and basic profile attributes.

Security Note:
All database interactions with this model are conducted strictly via
Django's ORM (e.g., CustomUser.objects.filter(...)), guaranteeing 100%
SQL injection immunity via auto-parameterization. No raw SQL is used.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """
    Custom user model for Sabin Balan Finance.
    Supports unique email authentication and non-unique usernames.
    """

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=False,
        help_text=_("Required. 150 characters or fewer.")
    )

    PROVIDER_CHOICES = (
        ('email', 'Standard Email/Password'),
        ('google', 'Google OAuth'),
        ('github', 'GitHub OAuth'),
        ('facebook', 'Facebook OAuth'),
    )

    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email address already exists."),
        },
        help_text=_("Required. Enter a valid email address.")
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    bio = models.TextField(
        _('bio'),
        blank=True,
        default="",
        help_text=_("Short bio or user profile description.")
    )

    avatar_url = models.URLField(
        _('avatar URL'),
        max_length=500,
        blank=True,
        default="",
        help_text=_("URL pointing to profile avatar image.")
    )

    auth_provider = models.CharField(
        _('authentication provider'),
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='email',
        help_text=_("Identifies the source provider used during user registration.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']

    def __str__(self):
        return self.username or self.email

    def get_display_name(self):
        """Returns full name or fallback username."""
        full_name = self.get_full_name().strip()
        return full_name if full_name else self.username

    def get_initials(self):
        """Generates 1-2 character initials for default avatar display."""
        name = self.get_display_name()
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return name[:2].upper() if name else "U"


class SuperUser(CustomUser):
    """
    Proxy model for CustomUser to represent and manage Superusers separately in the Django Admin.
    """
    class Meta:
        proxy = True
        verbose_name = _('Super User')
        verbose_name_plural = _('Super Users')


class FAQ(models.Model):
    """
    FAQ Model for managing Frequently Asked Questions on the home page.
    Allows full CRUD operations via Django Admin Panel.
    """
    CATEGORY_CHOICES = (
        ('general', 'General Advisory'),
        ('wealth', 'Wealth Management'),
        ('fiduciary', 'Fiduciary & Fees'),
        ('investment', 'SIP & Investment Limits'),
    )

    question = models.CharField(
        _('Question'),
        max_length=300,
        help_text=_("Enter the FAQ question text.")
    )
    answer = models.TextField(
        _('Answer'),
        help_text=_("Enter the detailed answer for this FAQ.")
    )
    category = models.CharField(
        _('Category'),
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='general',
        help_text=_("Category grouping for the FAQ item.")
    )
    order = models.PositiveIntegerField(
        _('Display Order'),
        default=0,
        help_text=_("Numerical order sequence for display (lower numbers appear first).")
    )
    is_active = models.BooleanField(
        _('Is Published'),
        default=True,
        help_text=_("Uncheck to hide this FAQ from the website.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQs')
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.question


class TeamMember(models.Model):
    """
    Model representing a Professional Wealth Advisor/Team Member.
    Allows complete management (create, update, delete) from the Admin Panel.
    """
    name = models.CharField(
        _('Name'),
        max_length=150,
        help_text=_("Full name of the team member.")
    )
    role = models.CharField(
        _('Role/Designation'),
        max_length=150,
        help_text=_("Corporate title or professional role.")
    )
    image = models.ImageField(
        _('Profile Image'),
        upload_to='team/',
        blank=True,
        null=True,
        help_text=_("Upload a high-quality portrait image. If empty, the default placeholder asset will be used.")
    )
    order = models.PositiveIntegerField(
        _('Display Order'),
        default=0,
        help_text=_("Used to order items in the UI. Lower values appear first.")
    )
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_("Uncheck to temporarily hide this member from the public layout.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Team Member')
        verbose_name_plural = _('Team Members')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def get_image_url(self):
        """Safely retrieves image URL from uploaded file or static filename string."""
        if not self.image:
            return ''
        name = str(self.image.name if hasattr(self.image, 'name') else self.image)
        if name in ["team_sabin.png", "about_showcase_team.png", "financial_advisors_team.png", "about_hero.png", "home_hero.png", "about_us_hero.png"]:
            from django.templatetags.static import static
            return static(name)
        try:
            return self.image.url
        except Exception:
            return ''

    @property
    def avatar_url(self):
        """Dynamic uploaded image URL or static avatar fallback based on display order."""
        url = self.get_image_url
        if url:
            return url
        from django.templatetags.static import static
        default_avatars = ['team_sabin.png', 'avatar_leader2.png', 'avatar_leader3.png', 'avatar_leader4.png']
        idx = max(0, (self.order or 1) - 1) % len(default_avatars)
        return static(default_avatars[idx])




class Testimonial(models.Model):
    """
    Model representing Client Testimonials & Global Reviews.
    Supports interactive galaxy positioning, verification badges, categories, and ratings.
    """
    CATEGORY_CHOICES = (
        ('entrepreneur', 'Entrepreneurs'),
        ('portfolio_manager', 'Portfolio Managers'),
        ('saver', 'Long-term Savers'),
        ('institutional', 'Institutional Investors'),
    )

    name = models.CharField(_('Client Name'), max_length=150)
    email = models.EmailField(_('Reviewer Email Address'), blank=True, default='')
    role = models.CharField(_('Professional Title / Role'), max_length=150)
    location = models.CharField(_('City / Region'), max_length=100, default='Global')
    quote = models.TextField(_('Testimonial Quote'))
    rating = models.PositiveSmallIntegerField(_('Star Rating (1-5)'), default=5)
    category = models.CharField(_('Category'), max_length=50, choices=CATEGORY_CHOICES, default='entrepreneur')
    avatar_image = models.CharField(_('Avatar Asset Name or URL'), max_length=255, blank=True, default='')
    avatar_file = models.ImageField(_('Uploaded Avatar Photo'), upload_to='testimonials/avatars/', blank=True, null=True)
    is_verified_linkedin = models.BooleanField(_('Verified via LinkedIn'), default=True)
    linkedin_url = models.URLField(_('LinkedIn Profile URL'), blank=True, default='https://linkedin.com')
    pos_x = models.FloatField(_('Map X Position (%)'), default=30.0, help_text=_("X percentage coordinate (0-100) on global map grid"))
    pos_y = models.FloatField(_('Map Y Position (%)'), default=40.0, help_text=_("Y percentage coordinate (0-100) on global map grid"))
    badge_theme = models.CharField(_('Glow Theme'), max_length=30, default='cyan', choices=[
        ('cyan', 'Cyan Glow'),
        ('emerald', 'Emerald Glow'),
        ('amber', 'Amber/Gold Glow'),
        ('violet', 'Violet Glow')
    ])
    card_type = models.CharField(_('Display Card Style'), max_length=30, default='bubble', choices=[
        ('bubble', 'Glowing Organic Bubble'),
        ('glass_card', 'Sleek Dark Glass Card'),
        ('node_only', 'Compact Avatar Node'),
    ])
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Testimonial')
        verbose_name_plural = _('Testimonials')
        ordering = ['order', '-rating', 'name']

    def __str__(self):
        return f"{self.name} ({self.role})"

    @property
    def get_avatar_url(self):
        """Safely retrieves avatar URL from uploaded file, image path string, or empty string."""
        if self.avatar_file:
            try:
                return self.avatar_file.url
            except ValueError:
                pass
        if self.avatar_image:
            return self.avatar_image
        return ''


class ConsultationBooking(models.Model):
    """
    Model representing Private Wealth Management & Financial Advisory Bookings.
    Includes unique 10-character reference key, dynamic scheduling buffers,
    status workflows, and admin rescheduling tracking with before/after comparison.
    """
    CONSULTATION_FEES = {
        30: 3000.00,
        45: 5000.00,
        60: 8000.00,
    }

    SERVICE_CHOICES = (
        ('financial_planning', 'Comprehensive Financial Planning'),
        ('investment', 'Investment & Multi-Asset Portfolio Strategy'),
        ('fixed_deposit', 'Fixed Deposit & High-Yield Preservation'),
        ('wealth_management', 'Private Wealth Management & Family Office'),
        ('retirement', 'Retirement & Legacy Structuring'),
        ('tax_planning', 'Tax Optimization & Fiscal Structuring'),
        ('portfolio_review', 'Institutional Portfolio Diagnostic & Health Check'),
        ('general', 'General Advisory & Wealth Strategy'),
        ('other', 'Bespoke Executive Financial Advisory'),
    )

    DURATION_CHOICES = (
        (30, '30 Minutes — Focused Consultation (₹3,000)'),
        (45, '45 Minutes — Strategic Consultation (₹5,000)'),
        (60, '60 Minutes — Comprehensive Consultation (₹8,000)'),
    )

    COMM_CHOICES = (
        ('video_call', 'Secure Video Conference (Zoom / Google Meet)'),
        ('in_person', 'In-Person Executive Desk (Main Office)'),
        ('phone', 'Direct Private Phone Call'),
        ('email', 'Written Strategic Advisory Briefing'),
    )

    STATUS_CHOICES = (
        ('received', 'Booking Received'),
        ('under_review', 'Pending Confirmation / Under Review'),
        ('confirmed', 'Confirmed & Fiduciary Allocated'),
        ('paid', 'Paid & Confirmed'),
        ('rescheduled', 'Rescheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_CHOICES = (
        ('unpaid', 'Unpaid / Payment Due'),
        ('paid', 'Paid / Completed'),
        ('waived', 'Complimentary / Fee Waived'),
        ('pending', 'Payment Processing / Pending Verification'),
        ('refunded', 'Refunded'),
    )

    reference_key = models.CharField(
        _('Reference Key'),
        max_length=10,
        unique=True,
        db_index=True,
        help_text=_("Unique 10-character alphanumeric tracking key (e.g., GT7K4M9P2X).")
    )
    client_name = models.CharField(_('Client Name'), max_length=150)
    email = models.EmailField(_('Email Address'))
    phone = models.CharField(_('Phone Number'), max_length=30)
    service = models.CharField(_('Consultation Service'), max_length=50, choices=SERVICE_CHOICES, default='financial_planning')
    duration_minutes = models.PositiveIntegerField(_('Duration (Minutes)'), choices=DURATION_CHOICES, default=45)
    consultation_date = models.DateField(_('Consultation Date'))
    consultation_time = models.TimeField(_('Consultation Start Time'))
    end_time = models.TimeField(_('Consultation End Time'), blank=True, null=True)
    
    # Financial Billing & Retainer Attributes (Dynamic Pricing in ₹ / INR)
    fee_amount = models.DecimalField(_('Consultation Fee (₹)'), max_digits=10, decimal_places=2, default=5000.00, help_text=_("Standard advisory fee in INR (₹3,000 for 30m, ₹5,000 for 45m, ₹8,000 for 60m)."))
    discount_amount = models.DecimalField(_('Discount / Waiver (₹)'), max_digits=10, decimal_places=2, default=0.00, help_text=_("Fee reduction or institutional promotional credit in INR."))
    net_amount = models.DecimalField(_('Net Amount Due (₹)'), max_digits=10, decimal_places=2, default=5000.00, help_text=_("Final net amount due or paid."))
    invoice_number = models.CharField(_('Invoice / Tax Ref Number'), max_length=50, blank=True, default='')
    payment_method = models.CharField(_('Payment Mode'), max_length=50, blank=True, default='UPI / Net Banking / Card')
    transaction_id = models.CharField(_('Transaction ID / UTR Ref'), max_length=100, blank=True, default='')
    fiduciary_desk = models.CharField(_('Assigned Fiduciary / Desk'), max_length=150, blank=True, default='Senior Wealth Advisory & Fiduciary Desk')
    meeting_link = models.CharField(_('Encrypted Meeting URL / Room Link'), max_length=500, blank=True, default='')
    client_instructions = models.TextField(
        _('Pre-Session Preparation Checklist'),
        blank=True,
        default='1. Secure encrypted meeting link will be dispatched 30 mins prior to schedule.\n2. Please have recent asset allocation summaries or tax returns ready.\n3. 24-hour advance notice requested for calendar adjustments.'
    )

    subject = models.CharField(_('Subject / Purpose'), max_length=255, blank=True, default='')
    message = models.TextField(_('Requirements / Message'), blank=True, default='')
    preferred_comm = models.CharField(
        _('Preferred Communication Method'),
        max_length=30,
        choices=COMM_CHOICES,
        default='video_call'
    )
    
    status = models.CharField(
        _('Booking Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='received'
    )
    payment_status = models.CharField(
        _('Payment Status'),
        max_length=30,
        choices=PAYMENT_CHOICES,
        default='unpaid'
    )
    
    admin_notes = models.TextField(_('Advisor / Admin Internal Notes'), blank=True, default='')
    
    # Rescheduling Audit Log Fields
    previous_date = models.DateField(_('Previous Consultation Date'), null=True, blank=True)
    previous_time = models.TimeField(_('Previous Consultation Time'), null=True, blank=True)
    rescheduled_reason = models.TextField(_('Rescheduling Reason / Note'), blank=True, default='')

    ip_address = models.GenericIPAddressField(_('Client IP Address'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Consultation Booking')
        verbose_name_plural = _('Consultation Bookings')
        ordering = ['-consultation_date', '-consultation_time', '-created_at']

    def __str__(self):
        time_str = self.consultation_time.strftime('%I:%M %p') if hasattr(self.consultation_time, 'strftime') else str(self.consultation_time or '')
        fee_str = f"₹{float(self.net_amount):,.0f}" if self.net_amount is not None else "₹0"
        return f"[{self.reference_key}] {self.client_name} — {self.get_service_display()} ({self.consultation_date} at {time_str}) - {fee_str}"

    @staticmethod
    def generate_unique_reference_key():
        """
        Generates a crisp, 10-character alphanumeric booking reference key
        (e.g., GT7K4M9P2X) excluding ambiguous letters/numbers (0, O, 1, I, L).
        """
        import secrets
        alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
        while True:
            key = "".join(secrets.choice(alphabet) for _ in range(10))
            if not ConsultationBooking.objects.filter(reference_key=key).exists():
                return key

    def save(self, *args, **kwargs):
        import datetime
        from decimal import Decimal

        if not self.reference_key:
            self.reference_key = ConsultationBooking.generate_unique_reference_key()

        # Dynamic pricing rule: 30m = ₹3000, 45m = ₹5000, 60m = ₹8000
        if not self.fee_amount or self.fee_amount == Decimal('0.00') or (self.pk is None and self.fee_amount == Decimal('5000.00') and self.duration_minutes != 45):
            self.fee_amount = Decimal(str(self.CONSULTATION_FEES.get(self.duration_minutes, 5000.00)))

        discount = Decimal(str(self.discount_amount or 0.00))
        fee = Decimal(str(self.fee_amount or 5000.00))
        
        # If marked as waived, set discount equal to full fee
        if self.payment_status == 'waived':
            discount = fee
            self.discount_amount = discount

        self.net_amount = max(Decimal('0.00'), fee - discount)

        if not self.invoice_number and self.reference_key:
            self.invoice_number = f"INV-{datetime.datetime.now().year}-{self.reference_key[:6]}"

        # Automatically calculate end_time based on consultation_time + duration_minutes
        if self.consultation_time and self.duration_minutes:
            base_datetime = datetime.datetime.combine(datetime.date.today(), self.consultation_time)
            end_datetime = base_datetime + datetime.timedelta(minutes=self.duration_minutes)
            self.end_time = end_datetime.time()

        # Rescheduling & Status Change Detection when updated
        is_new = self.pk is None
        old_status = None
        old_payment_status = None
        is_rescheduled = False
        previous_schedule = None
        updated_schedule = None

        if not is_new:
            orig = ConsultationBooking.objects.filter(pk=self.pk).first()
            if orig:
                old_status = orig.status
                old_payment_status = orig.payment_status
                date_changed = orig.consultation_date != self.consultation_date
                time_changed = orig.consultation_time != self.consultation_time
                if date_changed or time_changed:
                    self.previous_date = orig.consultation_date
                    self.previous_time = orig.consultation_time
                    if self.status not in ['cancelled', 'completed']:
                        self.status = 'rescheduled'
                    is_rescheduled = True
                    if orig.consultation_date and orig.consultation_time:
                        previous_schedule = f"{orig.consultation_date.strftime('%A, %d %B %Y')} at {orig.consultation_time.strftime('%I:%M %p')}"
                    if self.consultation_date and self.consultation_time:
                        updated_schedule = f"{self.consultation_date.strftime('%A, %d %B %Y')} at {self.consultation_time.strftime('%I:%M %p')}"

        super().save(*args, **kwargs)

        # Dispatch automated luxury email notifications
        try:
            from .emails import send_consultation_booking_email, send_consultation_status_email
            if is_new:
                send_consultation_booking_email(self)
            else:
                status_changed = (old_status is not None and old_status != self.status)
                payment_changed = (old_payment_status is not None and old_payment_status != self.payment_status)
                if status_changed or payment_changed or is_rescheduled:
                    send_consultation_status_email(
                        self,
                        old_status=old_status,
                        old_payment_status=old_payment_status,
                        is_rescheduled=is_rescheduled,
                        previous_schedule=previous_schedule,
                        updated_schedule=updated_schedule
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error dispatching consultation email: {e}")

    @property
    def duration_label(self):
        labels = {
            30: '30 Minutes (Focused Consultation)',
            45: '45 Minutes (Strategic Consultation)',
            60: '60 Minutes (Comprehensive Consultation)',
        }
        return labels.get(self.duration_minutes, f'{self.duration_minutes} Minutes')

    @property
    def fee_amount_display(self):
        return f"₹{self.fee_amount:,.2f}"

    @property
    def discount_amount_display(self):
        return f"₹{self.discount_amount:,.2f}"

    @property
    def net_amount_display(self):
        return f"₹{self.net_amount:,.2f}"

    @property
    def status_badge_class(self):
        mapping = {
            'received': 'badge-info',
            'under_review': 'badge-warning',
            'confirmed': 'badge-success',
            'paid': 'badge-gold',
            'rescheduled': 'badge-orange',
            'completed': 'badge-primary',
            'cancelled': 'badge-danger',
        }
        return mapping.get(self.status, 'badge-secondary')

    @property
    def payment_badge_class(self):
        mapping = {
            'paid': 'badge-success',
            'waived': 'badge-success',
            'unpaid': 'badge-danger',
            'pending': 'badge-warning',
            'refunded': 'badge-secondary',
        }
        return mapping.get(self.payment_status, 'badge-warning')


class MediaMention(models.Model):
    """
    Model for 'As featured in' media logos (Trust Signals).
    """
    name = models.CharField(_('Publication Name'), max_length=150)
    logo = models.ImageField(_('Logo Image'), upload_to='trust_signals/media_mentions/', blank=True, null=True)
    link = models.URLField(_('Article Link'), blank=True, default='')
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Media Mention')
        verbose_name_plural = _('Media Mentions')
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.name

    @property
    def get_logo_url(self):
        if self.logo:
            try:
                return self.logo.url
            except Exception:
                pass
        return ''


class PartnerIntegration(models.Model):
    """
    Model for banking/institutional partners (Trust Signals).
    """
    name = models.CharField(_('Partner Name'), max_length=150)
    logo = models.ImageField(_('Partner Logo'), upload_to='trust_signals/partners/', blank=True, null=True)
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Partner Integration')
        verbose_name_plural = _('Partner Integrations')
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.name

    @property
    def get_logo_url(self):
        if self.logo:
            try:
                return self.logo.url
            except Exception:
                pass
        return ''


class AdminSaaSSubscription(models.Model):
    """
    Model managing the SaaS License, 3-Month Free Trial, and Subscription Plans
    provided by VintushTech & KPRegTech for Sabin Balan (Founder of GuardianTree FP).
    """
    STATUS_CHOICES = (
        ('active_trial', 'Active 3-Month Free Trial'),
        ('active_paid', 'Active Paid Subscription'),
        ('grace_period', 'Grace Period Notice'),
        ('locked_expired', 'Access Expired & Locked'),
    )

    PLAN_CHOICES = (
        ('trial_3_months', '3 Months Free Trial (Complimentary)'),
        ('1_month', '1 Month Standard Plan ($49 / Rs. 3,999)'),
        ('3_months', '3 Months Quarterly Plan ($129 / Rs. 9,999)'),
        ('6_months', '6 Months Semi-Annual Plan ($229 / Rs. 17,999)'),
        ('1_year', '1 Year Enterprise Annual Plan ($399 / Rs. 29,999)'),
    )

    service_name = models.CharField(_('Service Name'), max_length=200, default='GuardianTree FP Executive Admin Panel')
    client_name = models.CharField(_('Client Name & Title'), max_length=200, default='Sabin Balan (Founder, GuardianTree FP)')
    client_email = models.EmailField(_('Client Billing Email'), default='sabin@guardiantreefp.com')
    provider_credits = models.CharField(_('Provider Credits'), max_length=255, default='VintushTech & KPRegTech')
    
    is_free_trial = models.BooleanField(_('Is Free Trial Active'), default=True)
    trial_start_date = models.DateTimeField(_('Trial Start Date'), auto_now_add=True)
    trial_duration_days = models.PositiveIntegerField(_('Trial Duration (Days)'), default=90)
    trial_end_date = models.DateTimeField(_('Trial End Date'), null=True, blank=True)
    
    subscription_status = models.CharField(_('Subscription Status'), max_length=50, choices=STATUS_CHOICES, default='active_trial')
    current_plan = models.CharField(_('Active Plan'), max_length=50, choices=PLAN_CHOICES, default='trial_3_months')
    paid_until = models.DateTimeField(_('Access Valid Until'), null=True, blank=True)
    
    license_key = models.CharField(_('Active License Key'), max_length=150, blank=True, default='')
    is_locked = models.BooleanField(_('Manually Lock Admin Panel'), default=False, help_text=_('Check to immediately lock the admin panel.'))
    
    notes = models.TextField(_('License / Audit Notes'), blank=True, default='Initial 3-month free trial granted by VintushTech & KPRegTech.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('SaaS Subscription & License')
        verbose_name_plural = _('SaaS Subscriptions & Licenses')

    def __str__(self):
        return f"{self.service_name} — {self.get_subscription_status_display()}"


class AdminBackupLog(models.Model):
    """
    Model logging continuous automated database snapshots and preservation events.
    """
    file_name = models.CharField(_('Backup File Name'), max_length=255)
    file_path = models.CharField(_('File Path'), max_length=500)
    file_size_kb = models.FloatField(_('File Size (KB)'), default=0.0)
    trigger_event = models.CharField(_('Trigger Event'), max_length=255, default='Admin Panel Operation')
    is_automated = models.BooleanField(_('Automated Snapshot'), default=True)
    status = models.CharField(_('Backup Status'), max_length=50, default='success')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Backup Snapshot Log')
        verbose_name_plural = _('Backup Snapshot Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} ({self.file_size_kb} KB)"


class SaaSInvoice(models.Model):
    """
    Model representing official SaaS subscription billing invoices issued by KPRegTech & VintushTech.
    """
    invoice_number = models.CharField(_('Invoice Number'), max_length=100, unique=True)
    client_name = models.CharField(_('Client Name'), max_length=200, default='Sabin Balan (Founder, GuardianTree FP)')
    client_email = models.EmailField(_('Client Email'), default='sabin@guardiantreefp.com')
    provider_name = models.CharField(_('Provider Name'), max_length=200, default='KPRegTech & VintushTech')
    plan_code = models.CharField(_('Plan Code'), max_length=50)
    plan_name = models.CharField(_('Plan Name'), max_length=200)
    amount_inr = models.DecimalField(_('Amount (INR)'), max_digits=12, decimal_places=2, default=0.0)
    amount_usd = models.DecimalField(_('Amount (USD)'), max_digits=12, decimal_places=2, default=0.0)
    master_key = models.CharField(_('Issued Master License Key'), max_length=150)
    duration_days = models.PositiveIntegerField(_('Duration (Days)'), default=30)
    issued_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(_('Access Valid Until'))
    status = models.CharField(_('Invoice Status'), max_length=50, default='paid', choices=[('paid', 'Paid & Issued'), ('pending', 'Pending Payment'), ('cancelled', 'Cancelled')])
    notes = models.TextField(_('Notes'), blank=True, default='')

    class Meta:
        verbose_name = _('SaaS Invoice')
        verbose_name_plural = _('SaaS Invoices')
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.invoice_number} — {self.plan_name} ({self.master_key})"


class SaaSRequestLog(models.Model):
    """
    Logs subscription renewal requests sent by the client (Sabin Balan) from the lock screen.
    """
    plan_code = models.CharField(_('Requested Plan Code'), max_length=50)
    plan_name = models.CharField(_('Requested Plan Name'), max_length=200)
    client_email = models.EmailField(_('Client Email'), default='sabin@guardiantreefp.com')
    status = models.CharField(_('Request Status'), max_length=50, default='pending', choices=[('pending', 'Pending KPRegTech Review'), ('approved', 'Key Issued & Approved'), ('rejected', 'Rejected')])
    requested_at = models.DateTimeField(auto_now_add=True)
    issued_invoice = models.ForeignKey(SaaSInvoice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _('SaaS Request Log')
        verbose_name_plural = _('SaaS Request Logs')
        ordering = ['-requested_at']

    def __str__(self):
        return f"Request for {self.plan_name} by {self.client_email} ({self.status})"


class MarketResource(models.Model):
    """
    Model for managing Market Intelligence: Insights & Resources cards,
    downloadable PDFs, whitepapers, and guides displayed on the home page.
    """
    CATEGORY_CHOICES = (
        ('Market Insight', 'Market Insight'),
        ('Whitepaper', 'Whitepaper'),
        ('Executive Guide', 'Executive Guide'),
        ('Research Report', 'Research Report'),
        ('Macro Analysis', 'Macro Analysis'),
    )

    title = models.CharField(_('Resource Title'), max_length=255, help_text=_("e.g. Q4 Macroeconomic Equity Outlook & Yield Curves"))
    category_badge = models.CharField(_('Category Badge'), max_length=100, default='Market Insight', choices=CATEGORY_CHOICES)
    description = models.TextField(_('Short Description'), help_text=_("Brief summary of the research report or whitepaper."))
    meta_reading_time = models.CharField(_('Reading Time / Format Tag'), max_length=100, default='📖 12 Min Read', help_text=_("e.g. 📖 12 Min Read or 📄 PDF Whitepaper"))
    meta_topic = models.CharField(_('Topic / Sector Tag'), max_length=100, default='Macro Analysis Q4 2026', help_text=_("e.g. Corporate Liquidity, Estate & Legacy Planning"))
    
    image = models.ImageField(_('Cover Image File'), upload_to='market_intel/', blank=True, null=True, help_text=_("Upload high-res cover image for card."))
    image_url_fallback = models.CharField(_('Fallback Image Path/URL'), max_length=500, blank=True, default='', help_text=_("Static path fallback, e.g. login/images/market_intel_equity.jpg"))
    
    pdf_file = models.FileField(_('Downloadable PDF File'), upload_to='market_intel_pdfs/', blank=True, null=True, help_text=_("Upload the full PDF document here for client download."))
    external_pdf_url = models.URLField(_('External PDF / Report URL'), max_length=500, blank=True, default='', help_text=_("Optional link to external PDF file if not uploading directly."))
    
    is_coming_soon = models.BooleanField(_('Is Coming Soon?'), default=True, help_text=_("If checked, button shows 'Coming Soon ⏳' toast. Uncheck to activate direct PDF download!"))
    button_text = models.CharField(_('Action Button Text'), max_length=100, default='Coming Soon ⏳', help_text=_("e.g. Download PDF 📄, Read Full Report →, or Coming Soon ⏳"))
    
    is_published = models.BooleanField(_('Published on Homepage?'), default=True, help_text=_("Toggle visibility of this resource on the website."))
    order = models.IntegerField(_('Display Order'), default=0, help_text=_("Lower numbers appear first on home page."))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Market Resource / PDF')
        verbose_name_plural = _('Market Intelligence & PDFs')
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.category_badge})"

    def get_cover_image_url(self):
        if self.image:
            return self.image.url
        if self.image_url_fallback:
            if self.image_url_fallback.startswith('/') or self.image_url_fallback.startswith('http'):
                return self.image_url_fallback
            return f"/static/{self.image_url_fallback}"
        return "/static/login/images/market_intel_equity.jpg"

    def get_download_url(self):
        if self.pdf_file:
            return self.pdf_file.url
        if self.external_pdf_url:
            return self.external_pdf_url
        return "#"
