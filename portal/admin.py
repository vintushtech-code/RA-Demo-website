from django.contrib import admin
from .models import (
    StockRecommendation,
    RecommendationUpdate,
    SEBIComplianceAuditLog,
    ClientWatchlist,
    PortalSectionConfig,
    ClientPortalAccessOverride,
    PortalWidgetConfig,
    PortalAnnouncement
)


class RecommendationUpdateInline(admin.TabularInline):
    model = RecommendationUpdate
    extra = 1
    fields = ('update_type', 'headline', 'message', 'new_stop_loss', 'timestamp')


@admin.register(StockRecommendation)
class StockRecommendationAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'action', 'sector', 'horizon', 'target_price', 'stop_loss', 'potential_upside_percent', 'status', 'published_at')
    list_filter = ('status', 'action', 'horizon', 'sector', 'published_at')
    search_fields = ('ticker', 'company_name', 'thesis_summary', 'sha256_hash')
    readonly_fields = ('id', 'sha256_hash', 'created_at', 'updated_at')
    inlines = [RecommendationUpdateInline]
    ordering = ('-published_at',)

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RecommendationUpdate)
class RecommendationUpdateAdmin(admin.ModelAdmin):
    list_display = ('recommendation', 'update_type', 'headline', 'timestamp')
    list_filter = ('update_type', 'timestamp')
    search_fields = ('recommendation__ticker', 'headline', 'message')
    ordering = ('-timestamp',)


@admin.register(SEBIComplianceAuditLog)
class SEBIComplianceAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation', 'action_type', 'logged_at', 'sha256_checksum')
    list_filter = ('action_type', 'logged_at')
    search_fields = ('recommendation__ticker', 'sha256_checksum', 'action_type')
    readonly_fields = ('recommendation', 'action_type', 'snapshot_payload', 'sha256_checksum', 'logged_at')
    ordering = ('-logged_at',)

    # SEBI Regulation 25 Mandate: Immutable record-keeping (No manual adds/edits/deletions allowed)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientWatchlist)
class ClientWatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'ticker', 'company_name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'ticker', 'company_name')
    ordering = ('-created_at',)


@admin.register(PortalSectionConfig)
class PortalSectionConfigAdmin(admin.ModelAdmin):
    list_display = ('title', 'section_key', 'is_enabled_globally', 'requires_premium', 'is_visible_in_nav', 'display_order', 'updated_at')
    list_editable = ('is_enabled_globally', 'requires_premium', 'is_visible_in_nav', 'display_order')
    list_filter = ('is_enabled_globally', 'requires_premium', 'is_visible_in_nav')
    search_fields = ('title', 'section_key', 'subtitle', 'url_name')
    ordering = ('display_order', 'title')


@admin.register(ClientPortalAccessOverride)
class ClientPortalAccessOverrideAdmin(admin.ModelAdmin):
    list_display = ('client', 'section', 'access_status', 'custom_badge', 'expires_at', 'granted_by', 'updated_at')
    list_editable = ('access_status', 'custom_badge')
    list_filter = ('access_status', 'section', 'expires_at')
    search_fields = ('client__username', 'client__email', 'section__title', 'notes')
    raw_id_fields = ('client', 'granted_by')
    ordering = ('client', 'section__display_order')

    def save_model(self, request, obj, form, change):
        if not obj.granted_by:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PortalWidgetConfig)
class PortalWidgetConfigAdmin(admin.ModelAdmin):
    list_display = ('title', 'widget_key', 'widget_type', 'target_tier', 'is_active', 'display_order', 'updated_at')
    list_editable = ('is_active', 'display_order', 'target_tier')
    list_filter = ('widget_type', 'target_tier', 'is_active')
    search_fields = ('title', 'widget_key', 'content_html')
    ordering = ('display_order', '-created_at')


@admin.register(PortalAnnouncement)
class PortalAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'announcement_type', 'target_tier', 'is_active', 'is_dismissible', 'start_date', 'end_date')
    list_editable = ('is_active', 'is_dismissible')
    list_filter = ('announcement_type', 'target_tier', 'is_active')
    search_fields = ('title', 'message')
    filter_horizontal = ('specific_clients',)
    ordering = ('-created_at',)
