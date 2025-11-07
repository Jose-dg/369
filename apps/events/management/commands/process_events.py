
import logging
from django.core.management.base import BaseCommand
from apps.events import services as event_services

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    A Django management command to process pending events.
    
    This command finds all events with a 'pending' status and attempts to process them
    using the logic defined in the events.services module.
    
    Example usage:
        python manage.py process_events
    """
    help = 'Processes all pending events from the event queue.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting event processing...'))
        
        try:
            event_services.process_pending_events()
            self.stdout.write(self.style.SUCCESS('Finished event processing successfully.'))
        except Exception as e:
            logger.error(f"An unexpected error occurred during event processing: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR('An error occurred during event processing. Check logs for details.'))

