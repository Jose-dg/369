from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event

@receiver(post_save, sender=Event)
def trigger_event_processing(sender, instance, created, **kwargs):
    """
    Signal receiver that triggers asynchronous event processing
    when a new Event is created with a 'pending' status.
    Routes to appropriate task based on topic.
    """
    if created and instance.status == 'pending':
        # Route based on topic to avoid conflicts
        if instance.topic == 'pos.invoice.received':
            # Use threading for invoice events (legacy)
            from .tasks import process_event_async
            process_event_async(instance.id)
        elif instance.topic == 'orders/create':
            # Shopify orders use Celery
            from apps.integrations.erpnext.tasks import create_erpnext_order_from_shopify_event
            create_erpnext_order_from_shopify_event.delay(instance.id)
        elif instance.topic == 'order.create':
            # Generic order creation uses Celery
            from apps.integrations.router.tasks import process_order_event
            process_order_event.delay(instance.id)
        # Add more topics as needed

