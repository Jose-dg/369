import logging
import json
from django.db import transaction
from apps.events.models import Event
from apps.integrations.alegra import services as alegra_services

logger = logging.getLogger(__name__)



def process_pending_events():
    """
    Fetches and processes all pending events.
    """
    pending_events = Event.objects.filter(status='pending').order_by('created_at')
    logger.info(f"Found {pending_events.count()} pending events to process.")
    
    for event in pending_events:
        process_event(event)



def process_event(event: Event):
    """
    Processes a single event, sending its payload to the corresponding integration.
    """
    if event.status not in ['pending', 'failed']:
        logger.warning(f"Event {event.id} has status '{event.status}' and will not be processed.")
        return

    with transaction.atomic():
        # Lock the event to prevent concurrent processing
        locked_event = Event.objects.select_for_update().get(id=event.id)
        
        if locked_event.status not in ['pending', 'failed']:
            return

        locked_event.status = 'processing'
        locked_event.attempts += 1
        locked_event.save()

    try:
        if locked_event.topic == 'pos.invoice.received':
            handle_invoice_event(locked_event)
        
        else:
            logger.warning(f"No handler for topic: {locked_event.topic}")
            locked_event.status = 'failed'
            locked_event.error = f"No handler for topic: {locked_event.topic}"

        # If successful, update status and clear previous errors
        locked_event.status = 'success'
        locked_event.error = None
        locked_event.save()
        logger.info(f"Event {locked_event.id} processed successfully.")

    except Exception as e:
        logger.error(f"Failed to process event {locked_event.id}: {e}", exc_info=True)
        
        error_message = str(e)
        # Check if it's a requests.exceptions.HTTPError and extract the response
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_message = f"Alegra API Error: {json.dumps(error_detail)}"
            except json.JSONDecodeError:
                error_message = f"Alegra API Error: {e.response.text}"
        
        # Update the event with the failure status and detailed error
        with transaction.atomic():
            failed_event = Event.objects.select_for_update().get(id=locked_event.id)
            failed_event.status = 'failed'
            failed_event.error = error_message
            failed_event.save()



def handle_invoice_event(event: Event):
    """
    Handles the logic for an invoice event by calling the Alegra service.
    """
    alegra_services.send_invoice_from_event(event)
    logger.info(f"Successfully handed off event {event.id} to Alegra service.")
