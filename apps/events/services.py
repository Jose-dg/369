
import logging
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

    if event.status != 'pending':

        logger.warning(f"Event {event.id} is not pending, skipping.")

        return



    with transaction.atomic():

        # Lock the event to prevent concurrent processing

        locked_event = Event.objects.select_for_update().get(id=event.id)

        if locked_event.status != 'pending':

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

            locked_event.last_error = f"No handler for topic: {locked_event.topic}"



        locked_event.status = 'success'

        locked_event.last_error = None

        locked_event.save()

        logger.info(f"Event {locked_event.id} processed successfully.")



    except Exception as e:

        logger.error(f"Failed to process event {locked_event.id}: {e}", exc_info=True)

        locked_event.status = 'failed'

        locked_event.last_error = str(e)

        locked_event.save()



def handle_invoice_event(event: Event):

    """

    Handles the logic for an invoice event by calling the Alegra service.

    """

    alegra_services.send_invoice_from_event(event)

    logger.info(f"Successfully handed off event {event.id} to Alegra service.")



