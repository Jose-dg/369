
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event
from .tasks import process_event_async

@receiver(post_save, sender=Event)
def trigger_event_processing(sender, instance, created, **kwargs):
    """
    Signal receiver that triggers asynchronous event processing
    when a new Event is created with a 'pending' status.
    """
    if created and instance.status == 'pending':
        process_event_async(instance.id)
