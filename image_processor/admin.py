from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import ImageProcessingSession, ImageProcessingRequest

@admin.register(ImageProcessingSession)
class ImageProcessingSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'created_at', 'get_image_count', 'get_processed_count', 'get_total_size']
    list_filter = ['created_at']
    search_fields = ['session_id']
    readonly_fields = ['session_id', 'created_at']
    actions = ['delete_selected_sessions']
    
    def get_image_count(self, obj):
        return obj.images.count()
    get_image_count.short_description = 'Total Images'
    
    def get_processed_count(self, obj):
        return obj.images.filter(is_processed=True).count()
    get_processed_count.short_description = 'Processed Images'
    
    def get_total_size(self, obj):
        total_size = sum(img.file_size or 0 for img in obj.images.all())
        if total_size < 1024:
            return f"{total_size} B"
        elif total_size < 1024 * 1024:
            return f"{total_size // 1024} KB"
        else:
            return f"{total_size // (1024 * 1024)} MB"
    get_total_size.short_description = 'Total Size'
    
    def delete_selected_sessions(self, request, queryset):
        """Custom action to delete sessions and their files"""
        deleted_count = 0
        for session in queryset:
            try:
                # Files will be automatically deleted by the signal
                session.delete()
                deleted_count += 1
            except Exception as e:
                self.message_user(request, f"Error deleting session {session.session_id}: {e}", level='ERROR')
        
        self.message_user(request, f"Successfully deleted {deleted_count} sessions and their files")
    delete_selected_sessions.short_description = "Delete selected sessions and all files"

@admin.register(ImageProcessingRequest)
class ImageProcessingRequestAdmin(admin.ModelAdmin):
    list_display = [
        'original_filename', 'session_link', 'dimensions_comparison', 
        'dpi', 'is_processed', 'file_size_display', 'created_at'
    ]
    list_filter = ['is_processed', 'dimension_unit', 'created_at', 'dpi']
    search_fields = ['original_filename', 'session__session_id']
    readonly_fields = ['created_at', 'processed_at', 'file_size', 'original_width', 'original_height', 'original_file_size']
    actions = ['delete_selected_requests']
    
    def session_link(self, obj):
        if obj.session:
            url = reverse('admin:image_processor_imageprocessingsession_change', args=[obj.session.id])
            return format_html('<a href="{}">{}</a>', url, obj.session.session_id)
        return '-'
    session_link.short_description = 'Session'
    
    def dimensions_comparison(self, obj):
        if obj.original_width and obj.original_height:
            return format_html(
                '<span style="color: green;">{}×{}</span> → <span style="color: blue;">{}×{}</span>',
                obj.original_width, obj.original_height,
                obj.output_width, obj.output_height
            )
        return f"{obj.output_width}×{obj.output_height}"
    dimensions_comparison.short_description = 'Dimensions (Original → Output)'
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size // 1024} KB"
            else:
                return f"{obj.file_size // (1024 * 1024)} MB"
        return '-'
    file_size_display.short_description = 'File Size'
    
    fieldsets = (
        ('Image Information', {
            'fields': ('session', 'original_image', 'processed_image', 'original_filename')
        }),
        ('Original Image Details', {
            'fields': ('original_width', 'original_height', 'original_file_size'),
            'classes': ('collapse',)
        }),
        ('Output Settings', {
            'fields': ('output_width', 'output_height', 'dpi')
        }),
        ('Physical Dimensions', {
            'fields': ('dimension_unit', 'dimension_width', 'dimension_height'),
            'classes': ('collapse',)
        }),
        ('Processing Status', {
            'fields': ('is_processed', 'created_at', 'processed_at', 'file_size'),
            'classes': ('collapse',)
        }),
    )
    
    def delete_selected_requests(self, request, queryset):
        """Custom action to delete requests and their files"""
        deleted_count = 0
        for request_obj in queryset:
            try:
                # Files will be automatically deleted by the signal
                request_obj.delete()
                deleted_count += 1
            except Exception as e:
                self.message_user(request, f"Error deleting request {request_obj.id}: {e}", level='ERROR')
        
        self.message_user(request, f"Successfully deleted {deleted_count} requests and their files")
    delete_selected_requests.short_description = "Delete selected requests and all files"
