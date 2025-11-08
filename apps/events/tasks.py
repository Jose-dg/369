
import threading
from django.db import connection
from .models import Event
from .services import handle_invoice_event

def _run_event_processing(event_id: str):
    """
    This function runs in a separate thread.
    It fetches the event and calls the main processing service.
    """
    try:
        event = Event.objects.get(id=event_id)
        handle_invoice_event(event)
    finally:
        # Django opens a DB connection per thread. It's crucial to close it
        # when the thread is done to avoid connection leaks.
        connection.close()

def process_event_async(event_id: str):
    """
    This function is called by the signal handler.
    It starts the background thread to process the event.
    """
    thread = threading.Thread(target=_run_event_processing, args=(event_id,))
    thread.daemon = True  # Allows the main application to exit even if threads are running
    thread.start()
