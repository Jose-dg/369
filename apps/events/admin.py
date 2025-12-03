from django.contrib import admin
from django.contrib import messages
from .models import Event

def retry_events(modeladmin, request, queryset):
    """
    Admin action to retry failed or pending events.
    Resets the event status to 'pending' and triggers reprocessing.
    """
    retriable_events = queryset.filter(status__in=['failed', 'pending'])
    count = retriable_events.count()
    
    if count == 0:
        modeladmin.message_user(
            request,
            "No failed or pending events selected.",
            level=messages.WARNING
        )
        return
    
    # Reset status to pending and clear error
    retriable_events.update(status='pending', error=None)
    
    # Trigger reprocessing via signal (or manually dispatch tasks)
    for event in retriable_events:
        # Route based on topic
        if event.topic == 'pos.invoice.received':
            from .tasks import process_event_async
            process_event_async(event.id)
        elif event.topic == 'orders/create':
            from apps.integrations.erpnext.tasks import create_erpnext_order_from_shopify_event
            create_erpnext_order_from_shopify_event.delay(event.id)
        elif event.topic == 'order.create':
            from apps.integrations.router.tasks import process_order_event
            process_order_event.delay(event.id)
    
    modeladmin.message_user(
        request,
        f"Successfully queued {count} event(s) for retry.",
        level=messages.SUCCESS
    )

retry_events.short_description = "Retry selected events"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'topic', 'status', 'organization', 'attempts', 'created_at')
    search_fields = ('source', 'topic', 'organization__slug', 'id')
    list_filter = ('status', 'source', 'topic', 'organization', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at', 'dedup_hash', 'trace_id')
    actions = [retry_events]
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'organization', 'source', 'topic', 'status')
        }),
        ('Processing', {
            'fields': ('attempts', 'error', 'response')
        }),
        ('Data', {
            'fields': ('payload', 'idempotency_key', 'dedup_hash', 'trace_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )