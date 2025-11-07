from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ResendInvoiceSerializer
from apps.events.models import Event
from apps.events.services import process_event
import logging

logger = logging.getLogger(__name__)

class ResendInvoiceAPIView(APIView):
    """
    API View to manually trigger the resending of an invoice to Alegra.
    """
    def post(self, request, *args, **kwargs):
        serializer = ResendInvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pos_invoice_name = serializer.validated_data['pos_invoice_name']
        logger.info(f"Received request to resend invoice: {pos_invoice_name}")

        # Find the original event associated with this POS invoice name.
        # We search within the JSON payload for the 'name' field.
        try:
            # Note: This assumes the organization is available on the request, 
            # which requires the TenantMiddleware to run for this endpoint.
            if not hasattr(request, 'organization'):
                return Response(
                    {"error": "Organization context not found. Please provide the X-Organization-Slug header."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            event_to_resend = Event.objects.get(
                organization=request.organization,
                payload__name=pos_invoice_name
            )
        except Event.DoesNotExist:
            logger.warning(f"Could not find an event for invoice name: {pos_invoice_name}")
            return Response(
                {"error": f"Event for invoice '{pos_invoice_name}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Event.MultipleObjectsReturned:
            logger.error(f"Found multiple events for invoice name: {pos_invoice_name}. Cannot proceed.")
            return Response(
                {"error": f"Multiple events found for '{pos_invoice_name}'. Manual intervention required."},
                status=status.HTTP_409_CONFLICT
            )

        # Reset the event status to 'pending' to allow reprocessing.
        # This is a simple approach. A more robust system might create a new event.
        event_to_resend.status = 'pending'
        event_to_resend.last_error = "Manually triggered for resend."
        event_to_resend.save()

        # Process the event immediately.
        try:
            process_event(event_to_resend)
            logger.info(f"Successfully re-processed event for invoice: {pos_invoice_name}")
            return Response(
                {"message": f"Invoice '{pos_invoice_name}' has been queued for resending."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"An error occurred during immediate reprocessing of {pos_invoice_name}: {e}", exc_info=True)
            return Response(
                {"error": "An error occurred during reprocessing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
