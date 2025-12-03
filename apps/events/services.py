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
        
        elif locked_event.topic == 'order.create':
            # We delegate to the Celery task, but since we are already in a processing loop here,
            # we might want to call the logic directly or trigger the task.
            # However, process_event seems to be designed for synchronous processing (e.g. cron).
            # If we want to reuse the task logic, we should probably import the logic or call the task synchronously.
            # Calling .delay() here would just queue it again, which might be fine but redundant if we want to process now.
            # But wait, the task ITSELF handles status updates (processing -> success/failed).
            # The current process_event ALSO handles status updates.
            # This creates a conflict if we just call the task.
            
            # Option 1: Call the task synchronously (apply).
            # Option 2: Refactor process_event to just dispatch tasks.
            
            # Given the existing code structure, process_event wraps the handler in try/except and updates status.
            # So the handler should just DO the work and raise exception on failure.
            # The new task I created `process_manual_order_event` does EVERYTHING (locking, status update).
            # So if I call it here, I should probably just trigger it and let it run, 
            # OR I should extract the logic.
            
            # To avoid code duplication and conflicts, let's just trigger the task asynchronously here 
            # and let this function return. 
            # BUT this function `process_event` sets status to 'processing' then 'success'.
            # If I trigger a task, this function will finish and set status to 'success' immediately, 
            # while the task is still running or queued. That's bad.
            
            # BETTER APPROACH:
            # Create a handler function `handle_manual_order_event` here that calls the backend synchronously,
            # similar to `handle_invoice_event`.
            # The Celery task `process_manual_order_event` can ALSO call this handler or similar logic.
            
            # Let's import the logic from the task I just created? 
            # Actually, I should have put the logic in a service and called it from both.
            
            # For now, to be safe and quick: I will implement `handle_manual_order_event` here 
            # which does the actual HTTP request.
            # And I will update the task I just created to use this handler or just keep them separate for now 
            # if they have different lifecycles.
            
            # Wait, the user wants me to use the task.
            # If `process_pending_events` is running, it picks up pending events.
            # If the view calls `.delay()`, the event is picked up by Celery.
            # We have a race condition if both run.
            # The view creates the event.
            # If I add the topic here, `process_pending_events` (cron) might pick it up.
            
            # I will add the handler here to support the "Cron/Script" way of processing,
            # just in case Celery is down or we want to run it manually.
            
            handle_order_event(locked_event)
        
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


def handle_order_event(event: Event):
    """
    Handles the logic for an order event by sending it to the Core Backend.
    Maps the gateway store_id to the backend store_id.
    """
    import requests
    from django.conf import settings
    from apps.companies.models import Company
    
    payload = event.payload.copy()  # Create a copy to avoid mutating the original
    core_url = settings.CORE_BACKEND_URL
    api_key = settings.CORE_BACKEND_API_KEY
    
    # Map gateway store_id to backend store_id
    gateway_store_id = payload.get('store_id')
    if gateway_store_id:
        try:
            company = Company.objects.get(id=gateway_store_id)
            # Get backend_store_id from metadata
            backend_store_id = company.metadata.get('metadata', {}).get('backend_store_id')
            
            if backend_store_id:
                logger.info(f"Mapping store_id: {gateway_store_id} -> {backend_store_id}")
                payload['store_id'] = backend_store_id
            else:
                logger.warning(f"No backend_store_id found in metadata for Company {gateway_store_id}")
        except Company.DoesNotExist:
            logger.error(f"Company {gateway_store_id} not found for store_id mapping")
    
    target_url = f"{core_url}/marketplaces/webhook/order/create/"
    
    headers = {
        'Content-Type': 'application/json',
    }
    if api_key:
        headers['Authorization'] = f"Api-Key {api_key}"

    logger.info(f"Sending order event {event.id} to {target_url}")
    
    response = requests.post(
        target_url,
        json=payload,
        headers=headers,
        timeout=30
    )
    
    response.raise_for_status()
    
    # Store response in event
    event.response = response.json()
    # We don't save here because process_event saves at the end.


