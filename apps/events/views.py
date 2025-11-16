from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.events.models import Event
from apps.events import services as event_services
import logging

logger = logging.getLogger(__name__)

class RetryEventView(APIView):
    def post(self, request, event_id, *args, **kwargs):
        """
        Retries a failed event by its ID.
        """
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'status': 'error', 'message': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        # Optionally, you might want to restrict which statuses can be retried
        if event.status not in ['failed', 'pending']:
            return Response(
                {'status': 'error', 'message': f'Event in status "{event.status}" cannot be retried.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status to pending to allow processing
        event.status = 'pending'
        event.save()

        try:
            event_services.process_event(event)
            return Response({'status': 'success', 'message': 'Event is being processed.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"An unexpected error occurred during event retry: {e}", exc_info=True)
            return Response({'status': 'error', 'message': 'An error occurred during event processing.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)