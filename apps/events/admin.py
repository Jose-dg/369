from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('source', 'topic', 'status', 'organization', 'created_at')
    search_fields = ('source', 'topic', 'organization__name')
    list_filter = ('status', 'source', 'topic', 'organization')
    readonly_fields = ('id', 'created_at', 'updated_at', 'payload', 'last_error', 'trace_id', 'dedup_hash')