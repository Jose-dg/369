import logging
import requests
from django.conf import settings
from django.db import transaction
from core.celery import app
from apps.events.models import Event

logger = logging.getLogger(__name__)

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_order_event(self, event_id):
    """
    Processes an order event by sending it to the Core Backend.
    """
    logger.info(f"Starting order processing for event_id: {event_id}")

    try:
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)
            
            if event.status not in ['pending', 'failed']:
                logger.warning(f"Event {event_id} is already processed or in progress. Status: {event.status}")
                return

            event.status = 'processing'
            event.attempts += 1
            event.save()

    except Event.DoesNotExist:
        logger.error(f"Event with id {event_id} not found.")
        return

    try:
        # Use the shared handler logic
        from apps.events.services import handle_order_event
        
        handle_order_event(event)
        
        # Success
        event.status = 'success'
        event.save()
        logger.info(f"Successfully processed order event {event_id}. Response: {event.response}")

    except Exception as e:
        logger.error(f"Failed to process order event {event_id}: {e}", exc_info=True)
        
        error_msg = str(e)
        # Check for request exception attributes if it was a request error
        if hasattr(e, 'response') and e.response is not None:
             try:
                 error_msg = f"Backend Error: {e.response.text}"
             except:
                 pass

        event.status = 'failed'
        event.error = error_msg
        event.save()
        
        # Retry if appropriate (e.g. connection error)
        # We need to import requests to check type if we want to be specific, 
        # or just retry on any exception that isn't a permanent failure.
        # For now, let's just log and fail, or retry blindly.
        # raise self.retry(exc=e)
