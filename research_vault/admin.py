from django.contrib import admin
from .models import ResearchDocument, DocumentAccessAssignment, DocumentAccessLog


class DocumentAccessAssignmentInline(admin.TabularInline):
    model = DocumentAccessAssignment
    extra = 1
    raw_id_fields = ('client',)
    fields = ('client', 'is_active', 'admin_notes', 'assigned_at')
    readonly_fields = ('assigned_at',)


@admin.register(ResearchDocument)
class ResearchDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_universal_premium', 'publication_date', 'file_size_kb', 'is_published')
    list_filter = ('category', 'is_universal_premium', 'is_published', 'publication_date')
    search_fields = ('title', 'description', 'checksum_sha256')
    readonly_fields = ('id', 'file_size_kb', 'checksum_sha256', 'created_at', 'updated_at')
    inlines = [DocumentAccessAssignmentInline]
    ordering = ('-publication_date', '-created_at')

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentAccessAssignment)
class DocumentAccessAssignmentAdmin(admin.ModelAdmin):
    list_display = ('document', 'client', 'is_active', 'assigned_at', 'assigned_by')
    list_filter = ('is_active', 'assigned_at')
    search_fields = ('document__title', 'client__username', 'client__email', 'admin_notes')
    raw_id_fields = ('document', 'client')
    readonly_fields = ('assigned_at',)
    ordering = ('-assigned_at',)

    def save_model(self, request, obj, form, change):
        if not obj.assigned_by:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'action', 'ip_address', 'accessed_at')
    list_filter = ('action', 'accessed_at')
    search_fields = ('document__title', 'user__username', 'user__email', 'ip_address', 'watermark_stamp')
    readonly_fields = ('document', 'user', 'action', 'ip_address', 'user_agent', 'watermark_stamp', 'accessed_at')
    ordering = ('-accessed_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
