from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.events.models import Event
import logging

logger = logging.getLogger(__name__)

class ErpNextPosInvoiceWebhookView(APIView):
    def post(self, request, *args, **kwargs):
        """
        Receives a webhook from ERPNext for a POS invoice, validates it,
        and stores it as a pending event for asynchronous processing.
        """
        if not hasattr(request, 'organization'):
            logger.warning("Webhook received without organization context.")
            return Response(
                {"error": "Organization context not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        payload = request.data
        print('JSON desde ERPNext', payload)
        organization = request.organization

        try:
            Event.objects.create(
                organization=organization,
                source='erpnext',
                topic='pos.invoice.received',
                payload=payload
            )
            return Response(
                {"message": "Webhook received and event created."},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(
                f"Failed to create event for organization {organization.slug}: {e}",
                exc_info=True
            )
            return Response(
                {"error": "Failed to process webhook."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )