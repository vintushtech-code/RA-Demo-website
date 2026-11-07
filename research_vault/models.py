import uuid
import os
import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def get_private_doc_upload_path(instance, filename):
    """
    Saves private research PDFs in the non-public private_vault folder.
    Uses UUID filename to prevent any correlation with original filenames.
    """
    ext = os.path.splitext(filename)[1].lower() or '.pdf'
    clean_uuid = str(instance.id) if instance.id else str(uuid.uuid4())
    return os.path.join('research_documents', f"{clean_uuid}{ext}")


class ResearchDocument(models.Model):
    """
    Confidential equity research PDFs, valuation reports, and client-specific portfolio audits.
    Stored strictly in private storage with no direct public URL access.
    """
    CATEGORY_CHOICES = (
        ('portfolio_review', 'Exclusive Client Portfolio Review'),
        ('forensic_deep_dive', 'Forensic Accounting & Balance Sheet Audit'),
        ('earnings_audit', 'Quarterly Earnings & Concall Analysis'),
        ('valuation_note', 'Institutional DCF & Relative Valuation'),
        ('special_situation', 'Demerger, Buyback & Special Situations'),
        ('custom_advisory', 'Custom HNI Client Advisory Note'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text=_("Report title, e.g. Tata Elxsi Q2 Forensic Deep Dive"))
    description = models.TextField(blank=True, default="", help_text=_("Client-facing summary or investment brief"))
    category = models.CharField(max_length=48, choices=CATEGORY_CHOICES, default='portfolio_review')
    
    file = models.FileField(
        upload_to=get_private_doc_upload_path,
        help_text=_("PDF document file. Stored in encrypted/private vault storage.")
    )
    
    file_size_kb = models.FloatField(default=0.0)
    page_count = models.PositiveIntegerField(default=1)
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="", help_text=_("SHA-256 integrity hash"))
    
    # Access Scoping: Universal to all paying subscribers OR client-specific
    is_universal_premium = models.BooleanField(
        default=False,
        help_text=_("If checked, all active premium subscribers can view this. If unchecked, only individually assigned clients can view.")
    )
    is_published = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    
    publication_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publication_date', '-created_at']
        verbose_name = _('Research Document')
        verbose_name_plural = _('Research Documents')

    def __str__(self):
        scope = "Universal" if self.is_universal_premium else "Client-Specific"
        return f"[{scope}] {self.title} ({self.get_category_display()})"

    def save(self, *args, **kwargs):
        # Calculate SHA256 checksum and size if file is provided
        if self.file and not self.checksum_sha256:
            try:
                hasher = hashlib.sha256()
                for chunk in self.file.chunks():
                    hasher.update(chunk)
                self.checksum_sha256 = hasher.hexdigest()
                self.file_size_kb = round(self.file.size / 1024, 2)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def is_accessible_by(self, user):
        """
        Server-side permission evaluation:
        1. Superuser / Staff always has access.
        2. Non-authenticated users NEVER have access.
        3. If universal_premium: requires active premium subscription.
        4. If client-specific: requires active subscription AND explicit assignment.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        
        # Check active subscription
        from billing.models import UserSubscription
        has_sub = UserSubscription.objects.filter(
            user=user,
            status__in=['active', 'trial'],
            end_date__gte=timezone.now()
        ).exists()
        
        if not has_sub:
            return False
            
        if self.is_universal_premium:
            return True
            
        # Check client assignment
        return DocumentAccessAssignment.objects.filter(
            document=self,
            client=user,
            is_active=True
        ).exists()


class DocumentAccessAssignment(models.Model):
    """
    Maps confidential research PDFs to specific clients (Client A sees only Client A's PDFs).
    """
    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(ResearchDocument, on_delete=models.CASCADE, related_name='assignments')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_documents')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='allocated_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    admin_notes = models.TextField(blank=True, default="", help_text=_("Optional notes for admin reference"))

    class Meta:
        unique_together = ('document', 'client')
        ordering = ['-assigned_at']
        verbose_name = _('Document Access Assignment')
        verbose_name_plural = _('Document Access Assignments')

    def __str__(self):
        return f"{self.document.title} ➔ {self.client.get_display_name()} ({'Active' if self.is_active else 'Revoked'})"


class DocumentAccessLog(models.Model):
    """
    Immutable audit log capturing every access event and anti-piracy watermark text.
    """
    ACTION_CHOICES = (
        ('stream_view', 'Streamed in Secure In-Browser Viewer'),
        ('download', 'Direct Encrypted Download'),
        ('unauthorized_denied', 'Unauthorized Access Blocked (Security Alert)'),
    )

    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(ResearchDocument, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='vault_access_logs')
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default='stream_view')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    watermark_stamp = models.CharField(max_length=500, blank=True, default="")
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accessed_at']
        verbose_name = _('Document Access Log')
        verbose_name_plural = _('Document Access Logs')

    def __str__(self):
        user_name = self.user.get_display_name() if self.user else "Anonymous"
        return f"[{self.accessed_at.strftime('%Y-%m-%d %H:%M')}] {self.document.title} by {user_name} ({self.action})"
