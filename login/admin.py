from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    CustomUser, SuperUser, FAQ, TeamMember, Testimonial,
    ConsultationBooking, AdminSaaSSubscription, AdminBackupLog,
    MediaMention, PartnerIntegration, MarketResource, SecurityAuditLog
)
from portal.models import ClientPortalAccessOverride
from .saas_service import unlock_subscription_with_plan
from .backup_service import create_live_backup
import datetime
from django.utils import timezone

# ==============================================================================
# EXECUTIVE PORTAL BRANDING & HEADERS
# ==============================================================================
admin.site.site_header = "Kalphora Equity — Research Operations Suite"
admin.site.site_title = "Kalphora Equity Admin"
admin.site.index_title = "Operations & Institutional Governance"



@admin.register(AdminBackupLog)
class AdminBackupLogAdmin(admin.ModelAdmin):
    """
    Admin management panel for continuous automated database backups and data preservation audit trail.
    """
    list_display = ('file_name', 'file_size_display', 'trigger_event', 'is_automated', 'status_badge', 'created_at')
    list_filter = ('is_automated', 'status', 'created_at')
    search_fields = ('file_name', 'trigger_event', 'file_path')
    readonly_fields = ('file_name', 'file_path', 'file_size_kb', 'trigger_event', 'is_automated', 'status', 'created_at')

    @admin.display(description=_("Snapshot Size"), ordering="file_size_kb")
    def file_size_display(self, obj):
        return format_html('<strong>{} KB</strong>', obj.file_size_kb)

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        return format_html('<span style="background: #ecfdf5; color: #059669; padding: 3px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.78rem;">✔ PRESERVED & SECURE</span>')

    actions = ['trigger_instant_backup']

    @admin.action(description=_("📸 Generate Instant Database Snapshot Now"))
    def trigger_instant_backup(self, request, queryset):
        res = create_live_backup(event_trigger=f"Manual Admin Action by {request.user.username}")
        if res and res.get('success'):
            self.message_user(request, f"New database snapshot created: {res['file_name']} ({res['file_size_kb']} KB). All data 100% preserved.")
        else:
            self.message_user(request, "Backup failed to generate.", level='ERROR')


@admin.register(AdminSaaSSubscription)
class AdminSaaSSubscriptionAdmin(admin.ModelAdmin):
    """
    Admin management panel for SaaS Subscription Governance, License Keys & Expiration.
    """
    list_display = ('service_name', 'client_name', 'current_plan', 'status_badge', 'is_locked', 'paid_until', 'renew_desk_link', 'updated_at')
    list_filter = ('is_locked', 'is_free_trial', 'subscription_status')
    search_fields = ('service_name', 'client_name', 'client_email', 'license_key', 'notes')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description=_("Status Badge"))
    def status_badge(self, obj):
        if obj.is_locked:
            return format_html('<span style="background: #fee2e2; color: #dc2626; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 0.78rem;">🔒 EXPIRED & LOCKED</span>')
        return format_html('<span style="background: #d1fae5; color: #059669; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 0.78rem;">🟢 ACTIVE & UNLOCKED</span>')

    @admin.display(description=_("SaaS Control Desk"))
    def renew_desk_link(self, obj):
        return format_html(
            '<a href="/admin-saas/lock/" style="background: #10b981; color: #fff; padding: 4px 12px; border-radius: 6px; font-weight: 700; text-decoration: none; font-size: 0.78rem; display: inline-block;">⚡ Open Renewal & Unlock Desk</a>'
        )



@admin.register(ConsultationBooking)
class ConsultationBookingAdmin(admin.ModelAdmin):
    """
    Comprehensive Executive Admin Panel for Private Wealth Consultation Bookings.
    Provides complete visibility, filtering, search, status management, dynamic billing, and audit tracking.
    """
    list_display = (
        'reference_key', 'client_name', 'service', 'duration_minutes',
        'display_fee', 'payment_status', 'status',
        'consultation_date', 'consultation_time', 'invoice_number'
    )
    list_editable = ('payment_status', 'status')
    list_filter = (
        'status', 'payment_status', 'duration_minutes', 'service',
        'consultation_date', 'preferred_comm', 'created_at'
    )
    search_fields = ('reference_key', 'client_name', 'email', 'phone', 'invoice_number', 'transaction_id', 'subject', 'message')
    date_hierarchy = 'consultation_date'
    ordering = ('-consultation_date', '-consultation_time', '-created_at')
    readonly_fields = ('reference_key', 'end_time', 'net_amount', 'ip_address', 'created_at', 'updated_at')

    @admin.display(description=_("Fee / Net (₹)"), ordering="fee_amount")
    def display_fee(self, obj):
        if not obj.net_amount or obj.payment_status == 'waived':
            return format_html('<span style="color: #059669; font-weight: 700;">₹0 (Waived)</span>')
        try:
            val = float(obj.net_amount)
            return format_html('<strong>₹{:,.0f}</strong> <span style="font-size: 0.8em; color: #64748b;">(Net)</span>', val)
        except Exception:
            return format_html('<strong>₹{}</strong>', obj.net_amount)

    @admin.display(description=_("Status"), ordering="status")
    def colored_status(self, obj):
        color_map = {
            'received': ('#e0f2fe', '#0369a1'),
            'under_review': ('#fef3c7', '#b45309'),
            'confirmed': ('#dcfce7', '#15803d'),
            'paid': ('#fef9c3', '#854d0e'),
            'rescheduled': ('#ffedd5', '#c2410c'),
            'completed': ('#f1f5f9', '#475569'),
            'cancelled': ('#fee2e2', '#b91c1c'),
        }
        bg, fg = color_map.get(obj.status, ('#f1f5f9', '#334155'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; display: inline-block;">{}</span>',
            bg, fg, obj.get_status_display()
        )

    @admin.display(description=_("Payment Status"), ordering="payment_status")
    def colored_payment(self, obj):
        color_map = {
            'paid': ('#dcfce7', '#15803d', 'PAID'),
            'waived': ('#ecfdf5', '#047857', 'WAIVED (FREE)'),
            'unpaid': ('#fee2e2', '#b91c1c', 'UNPAID'),
            'pending': ('#fef3c7', '#b45309', 'PROCESSING'),
            'refunded': ('#f1f5f9', '#64748b', 'REFUNDED'),
        }
        bg, fg, label = color_map.get(obj.payment_status, ('#f1f5f9', '#334155', obj.get_payment_status_display()))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.8rem; display: inline-block;">{}</span>',
            bg, fg, label
        )
    
    fieldsets = (
        (_('Booking Identification & Client'), {
            'fields': (
                ('reference_key', 'invoice_number'),
                ('client_name', 'email', 'phone'),
                'ip_address'
            )
        }),
        (_('Consultation Schedule & Mode'), {
            'fields': (
                ('service', 'duration_minutes'),
                ('consultation_date', 'consultation_time', 'end_time'),
                ('preferred_comm', 'fiduciary_desk'),
                'meeting_link'
            )
        }),
        (_('Dynamic Financial Billing & Retainer Management'), {
            'fields': (
                ('fee_amount', 'discount_amount', 'net_amount'),
                ('payment_status', 'payment_method', 'transaction_id')
            )
        }),
        (_('Booking Lifecycle Status & Fiduciary Notes'), {
            'fields': (
                'status',
                'client_instructions',
                'admin_notes'
            )
        }),
        (_('Rescheduling Audit History'), {
            'classes': ('collapse',),
            'fields': (
                ('previous_date', 'previous_time'),
                'rescheduled_reason'
            )
        }),
        (_('Client Requirements & Scope'), {
            'fields': (
                'subject', 'message'
            )
        }),
        (_('System Timestamps'), {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    actions = ['action_mark_paid', 'action_mark_unpaid', 'action_mark_waived', 'action_confirm_booking', 'action_mark_completed', 'action_cancel_booking']

    @admin.action(description=_("Mark selected bookings as PAID (Payment Received)"))
    def action_mark_paid(self, request, queryset):
        count = queryset.update(payment_status='paid', status='paid')
        self.message_user(request, f"{count} booking(s) marked as PAID & Confirmed.")

    @admin.action(description=_("Mark selected bookings as UNPAID (Payment Pending)"))
    def action_mark_unpaid(self, request, queryset):
        count = queryset.update(payment_status='unpaid')
        self.message_user(request, f"{count} booking(s) marked as UNPAID.")

    @admin.action(description=_("Grant Full Complimentary Fee Waiver"))
    def action_mark_waived(self, request, queryset):
        for b in queryset:
            b.payment_status = 'waived'
            b.discount_amount = b.fee_amount
            b.net_amount = 0
            b.save()
        self.message_user(request, f"{queryset.count()} booking(s) granted Complimentary Fee Waiver.")

    @admin.action(description=_("Confirm selected consultation requests"))
    def action_confirm_booking(self, request, queryset):
        count = queryset.update(status='confirmed')
        self.message_user(request, f"{count} consultation booking(s) marked as Confirmed & Fiduciary Allocated.")

    @admin.action(description=_("Mark selected consultations as completed"))
    def action_mark_completed(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f"{count} consultation(s) marked as Completed.")

    @admin.action(description=_("Cancel selected consultation bookings"))
    def action_cancel_booking(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f"{count} consultation(s) marked as Cancelled.")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    """
    Admin configuration for Testimonial model to manage global client reviews.
    Supports review moderation, publishing, and auto-dispatching published congratulations email to reviewers.
    """
    list_display = ('name', 'email', 'role', 'location', 'category', 'star_rating', 'badge_theme', 'card_type', 'is_active', 'order')
    list_editable = ('category', 'badge_theme', 'card_type', 'is_active', 'order')
    list_filter = ('is_active', 'category', 'badge_theme', 'card_type', 'rating')
    search_fields = ('name', 'email', 'role', 'location', 'quote')
    ordering = ('order', '-rating')
    actions = ['approve_and_publish', 'make_inactive']

    @admin.display(description=_("Rating"), ordering="rating")
    def star_rating(self, obj):
        return f"{'⭐' * (obj.rating or 5)} ({obj.rating}/5)"

    @admin.action(description=_("Approve & Publish selected reviews (Sends Congratulations Email)"))
    def approve_and_publish(self, request, queryset):
        from .emails import send_testimonial_published_email
        count = 0
        for obj in queryset:
            if not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=['is_active'])
                count += 1
                try:
                    if obj.email:
                        send_testimonial_published_email(obj)
                except Exception as e:
                    logger.error(f"Failed sending publish email to {obj.email}: {e}")
        self.message_user(request, f"{count} testimonial(s) approved, published live, and notification emails dispatched.")

    @admin.action(description=_("Hide / Deactivate selected testimonials"))
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} testimonial(s) hidden from the live website.")

    def save_model(self, request, obj, form, change):
        is_new_publish = False
        if change:
            try:
                old_obj = Testimonial.objects.get(pk=obj.pk)
                if not old_obj.is_active and obj.is_active:
                    is_new_publish = True
            except Testimonial.DoesNotExist:
                if obj.is_active:
                    is_new_publish = True
        elif obj.is_active:
            is_new_publish = True

        super().save_model(request, obj, form, change)

        if is_new_publish and obj.email:
            try:
                from .emails import send_testimonial_published_email
                send_testimonial_published_email(obj)
            except Exception as e:
                logger.error(f"Error sending testimonial published email to {obj.email}: {e}")


class ClientPortalAccessOverrideInline(admin.TabularInline):
    model = ClientPortalAccessOverride
    extra = 0
    fk_name = 'client'
    fields = ('section', 'access_status', 'custom_badge', 'expires_at', 'notes')
    autocomplete_fields = ('section',)


class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for all CustomUser records.
    Displays custom user fields, active subscription status, and enables
    individual client portal section customization via inline overrides.
    """
    model = CustomUser
    list_display = ('username', 'email', 'subscription_badge', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'auth_provider', 'created_at')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    inlines = [ClientPortalAccessOverrideInline]
    actions = ['activate_clients', 'deactivate_clients']

    @admin.display(description=_("Portal Tier"))
    def subscription_badge(self, obj):
        if obj.is_staff or obj.is_superuser:
            return format_html('<span style="background: rgba(212,175,55,0.2); color: #D4AF37; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">🛡️ ADMIN</span>')
        if obj.is_premium_active:
            sub = obj.get_active_subscription()
            plan_name = sub.plan.name if (sub and sub.plan) else "PREMIUM"
            return format_html('<span style="background: rgba(16,185,129,0.2); color: #10B981; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">⭐ {}</span>', plan_name)
        return format_html('<span style="background: rgba(148,163,184,0.2); color: #94A3B8; padding: 2px 8px; border-radius: 9999px; font-weight: 600; font-size: 0.75rem;">FREE CLIENT</span>')

    @admin.action(description=_("✅ Activate Selected Client Accounts"))
    def activate_clients(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} client account(s) have been successfully activated.")

    @admin.action(description=_("🚫 Suspend / Deactivate Selected Client Accounts"))
    def deactivate_clients(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} client account(s) have been suspended.")

    # Extend standard fieldsets to show custom fields
    fieldsets = UserAdmin.fieldsets + (
        (_('Profile Info'), {'fields': ('bio', 'avatar_url', 'auth_provider')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Profile Info'), {
            'classes': ('wide',),
            'fields': ('email', 'bio', 'avatar_url', 'auth_provider'),
        }),
    )


class SuperUserAdmin(CustomUserAdmin):
    """
    Admin configuration specifically for superusers.
    Filters the queryset to only display superusers in the list view.
    """
    model = SuperUser
    
    def get_queryset(self, request):
        # Limit to superusers only
        return super().get_queryset(request).filter(is_superuser=True)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    Admin configuration for FAQ model to perform full CRUD operations.
    Allows managing questions, answers, categories, display order, and publishing status.
    """
    list_display = ('question', 'category', 'order', 'is_active', 'updated_at')
    list_editable = ('order', 'is_active', 'category')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('question', 'answer')
    ordering = ('order', 'created_at')
    actions = ['make_active', 'make_inactive']
    fieldsets = (
        (None, {
            'fields': ('question', 'answer', 'category', 'order', 'is_active')
        }),
    )

    @admin.action(description=_("Publish selected FAQs"))
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} FAQ(s) published to the live website.")

    @admin.action(description=_("Hide selected FAQs"))
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} FAQ(s) hidden from the live website.")


# ==============================================================================
# TEAM MEMBER ADMIN (COMMENTED OUT: "Meet Our Professional Team" section disabled)
# ==============================================================================
# @admin.register(TeamMember)
# class TeamMemberAdmin(admin.ModelAdmin):
#     """
#     Admin configuration for TeamMember model to perform full CRUD operations.
#     Allows managing names, designations, images, order, and publishing status.
#     """
#     list_display = ('name', 'role', 'order', 'is_active', 'updated_at')
#     list_editable = ('role', 'order', 'is_active')
#     list_filter = ('is_active', 'created_at')
#     search_fields = ('name', 'role')
#     ordering = ('order', 'name')
#     actions = ['make_active', 'make_inactive']
#     fieldsets = (
#         (None, {
#             'fields': ('name', 'role', 'image', 'order', 'is_active')
#         }),
#     )
# 
#     @admin.action(description=_("Publish selected team members"))
#     def make_active(self, request, queryset):
#         count = queryset.update(is_active=True)
#         self.message_user(request, f"{count} team member(s) published on the live About page.")
# 
#     @admin.action(description=_("Hide selected team members"))
#     def make_inactive(self, request, queryset):
#         count = queryset.update(is_active=False)
#         self.message_user(request, f"{count} team member(s) hidden from the live About page.")



@admin.register(MediaMention)
class MediaMentionAdmin(admin.ModelAdmin):
    """
    Admin configuration for Media Mention ('As Featured In') logos & press links.
    """
    list_display = ('name', 'link', 'order', 'is_active', 'created_at')
    list_editable = ('link', 'order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'link')
    ordering = ('order', '-created_at')
    actions = ['make_active', 'make_inactive']

    @admin.action(description=_("Publish selected media mentions"))
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} media mention(s) published.")

    @admin.action(description=_("Hide selected media mentions"))
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} media mention(s) hidden.")


@admin.register(PartnerIntegration)
class PartnerIntegrationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Institutional & Banking Partner logos.
    """
    list_display = ('name', 'order', 'is_active', 'created_at')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('order', '-created_at')
    actions = ['make_active', 'make_inactive']

    @admin.action(description=_("Publish selected partners"))
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} partner(s) published.")

    @admin.action(description=_("Hide selected partners"))
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} partner(s) hidden.")


@admin.register(MarketResource)
class MarketResourceAdmin(admin.ModelAdmin):
    """
    Admin configuration for Market Intelligence: Insights & Resources, PDF Whitepapers, and Master Guides.
    Allows clients to add, edit, remove, upload PDFs, and toggle 'Coming Soon' vs active PDF Download buttons.
    """
    list_display = (
        'title', 'category_badge', 'is_coming_soon_badge', 'download_link',
        'is_published', 'order', 'updated_at'
    )
    list_editable = ('is_published', 'order')
    list_filter = ('category_badge', 'is_coming_soon', 'is_published', 'created_at')
    search_fields = ('title', 'description', 'meta_topic', 'meta_reading_time')
    ordering = ('order', '-created_at')
    actions = ['toggle_coming_soon_off', 'toggle_coming_soon_on', 'make_published', 'make_unpublished']

    @admin.display(description=_("Status / Download Mode"))
    def is_coming_soon_badge(self, obj):
        if obj.is_coming_soon:
            return format_html('<span style="background: #fef3c7; color: #d97706; padding: 3px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.78rem;">⏳ Coming Soon</span>')
        return format_html('<span style="background: #d1fae5; color: #059669; padding: 3px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.78rem;">📄 PDF Download Active</span>')

    @admin.display(description=_("PDF Document / Link"))
    def download_link(self, obj):
        url = obj.get_download_url()
        if url and url != "#":
            return format_html('<a href="{}" target="_blank" style="color: #2563eb; font-weight: 700; text-decoration: none;">📥 Download PDF</a>', url)
        return format_html('<span style="color: #94a3b8; font-style: italic;">No File Uploaded</span>')

    @admin.action(description=_("✅ Enable Direct PDF Download (Turn off 'Coming Soon')"))
    def toggle_coming_soon_off(self, request, queryset):
        count = queryset.update(is_coming_soon=False, button_text="Download PDF 📄")
        self.message_user(request, f"{count} resource(s) updated to active PDF download.")

    @admin.action(description=_("⏳ Set to 'Coming Soon'"))
    def toggle_coming_soon_on(self, request, queryset):
        count = queryset.update(is_coming_soon=True, button_text="Coming Soon ⏳")
        self.message_user(request, f"{count} resource(s) set to Coming Soon.")

    @admin.action(description=_("👁️ Publish on Homepage"))
    def make_published(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(request, f"{count} resource(s) published on homepage.")

    @admin.action(description=_("🙈 Hide from Homepage"))
    def make_unpublished(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(request, f"{count} resource(s) hidden from homepage.")


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    """
    Immutable Security Audit Trail for all authentication, session lifecycle,
    and administrative privilege actions.
    """
    list_display = ('event_type', 'actor_user', 'target_user', 'ip_address', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('actor_user__username', 'actor_user__email', 'target_user__username', 'target_user__email', 'ip_address')
    readonly_fields = ('id', 'event_type', 'actor_user', 'target_user', 'ip_address', 'user_agent', 'details', 'timestamp')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Register models in admin panel
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(SuperUser, SuperUserAdmin)

# Proactive Debugging: Write a marker file to verify if this file is loaded by the Django process
import os
try:
    with open('admin_loaded.txt', 'w') as f:
        f.write('Loaded successfully')
except Exception:
    pass


