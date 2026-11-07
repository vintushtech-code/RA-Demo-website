import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import ContactSubmission


@admin.action(description="Export selected submissions to CSV")
def export_submissions_to_csv(modeladmin, request, queryset):
    """Custom admin action to export selected submissions to a CSV file."""
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="contact_submissions.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(["ID", "Name", "Email", "Subject", "Status", "Message", "IP Address", "Created At", "Resolved At"])
    
    for submission in queryset:
        created_at_local = localtime(submission.created_at).strftime('%Y-%m-%d %H:%M:%S')
        resolved_at_local = localtime(submission.resolved_at).strftime('%Y-%m-%d %H:%M:%S') if submission.resolved_at else ""
        writer.writerow([
            submission.id,
            submission.name,
            submission.email,
            submission.subject,
            submission.status,
            submission.message,
            submission.ip_address,
            created_at_local,
            resolved_at_local,
        ])
    return response


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status_badge', 'message_snippet', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message', 'admin_notes')
    readonly_fields = ('name', 'email', 'subject', 'message', 'ip_address', 'created_at', 'resolved_at')
    actions = [
        'mark_as_resolved',
        'mark_as_read',
        'mark_as_new',
        export_submissions_to_csv
    ]

    fieldsets = (
        (_('Inquiry Details'), {
            'fields': ('name', 'email', 'subject', 'message', 'ip_address', 'created_at')
        }),
        (_('Administrative Resolution & Notes'), {
            'fields': ('status', 'admin_notes', 'resolved_at')
        }),
    )

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            'new': ('rgba(234, 179, 8, 0.2)', '#FBBF24', '🆕 NEW'),
            'read': ('rgba(59, 130, 246, 0.2)', '#60A5FA', '👁️ IN REVIEW'),
            'resolved': ('rgba(16, 185, 129, 0.2)', '#10B981', '✅ RESOLVED'),
            'archived': ('rgba(148, 163, 184, 0.2)', '#94A3B8', '📁 ARCHIVED'),
        }
        bg, fg, label = colors.get(obj.status, ('rgba(148, 163, 184, 0.2)', '#94A3B8', obj.status))
        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">{}</span>',
            bg, fg, label
        )

    @admin.display(description=_("Message Preview"))
    def message_snippet(self, obj):
        text = obj.message or ""
        snippet = (text[:50] + '...') if len(text) > 50 else text
        return format_html('<span style="color: var(--admin-text-secondary); font-style: italic;">{}</span>', snippet)

    @admin.action(description=_("✅ Mark Selected Inquiries as Resolved"))
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f"{updated} inquiry/messages marked as Resolved.")

    @admin.action(description=_("👁️ Mark Selected Inquiries as In Review / Read"))
    def mark_as_read(self, request, queryset):
        updated = queryset.update(status='read')
        self.message_user(request, f"{updated} inquiry/messages marked as In Review.")

    @admin.action(description=_("🆕 Mark Selected Inquiries as New / Unread"))
    def mark_as_new(self, request, queryset):
        updated = queryset.update(status='new', resolved_at=None)
        self.message_user(request, f"{updated} inquiry/messages reset to New / Unread.")

    def has_add_permission(self, request):
        return False
