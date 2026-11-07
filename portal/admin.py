from django.contrib import admin
from .models import StockRecommendation, RecommendationUpdate, SEBIComplianceAuditLog, ClientWatchlist


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
