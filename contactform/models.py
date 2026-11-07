from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ContactSubmission(models.Model):
    """
    Client inquiry and communication message model.
    Tracks sender identity, message content, client IP, and administrative resolution status.
    """
    STATUS_CHOICES = (
        ('new', '🆕 New / Unread'),
        ('read', '👁️ In Review / Read'),
        ('resolved', '✅ Resolved / Addressed'),
        ('archived', '📁 Archived'),
    )

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    admin_notes = models.TextField(blank=True, default="", help_text=_("Internal administrative notes or follow-up summary."))
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Contact Inquiry')
        verbose_name_plural = _('Contact Inquiries & Messages')

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name} - {self.subject} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
