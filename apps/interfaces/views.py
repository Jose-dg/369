import logging
import hmac
import hashlib
import base64
from urllib.parse import urlparse

from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.companies.models import Company
from apps.events.models import Event
from apps.integrations.erpnext.tasks import create_erpnext_order_from_shopify_event


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
        logger.info(f"JSON received from Shopify: {payload}")
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


def verify_shopify_webhook(request, webhook_secret):
    """
    Verifies the HMAC signature of an incoming Shopify webhook.
    """
    received_hmac = request.headers.get("X-Shopify-Hmac-Sha256")
    if not received_hmac:
        return False

    computed_hmac = base64.b64encode(
        hmac.new(
            webhook_secret.encode("utf-8"),
            request.body, # Use the raw request body
            hashlib.sha256
        ).digest()
    ).decode("utf-8")

    return hmac.compare_digest(received_hmac, computed_hmac)


@method_decorator(csrf_exempt, name='dispatch')
class ShopifyOrderWebhookView(APIView):
    """
    Receives, validates, and enqueues order-related webhooks from Shopify.
    """

    def post(self, request, *args, **kwargs):
        payload = request.data

        order_status_url = payload.get('order_status_url')
        if not order_status_url:
            return Response(
                {'error': 'Payload is missing order_status_url'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            hostname = urlparse(order_status_url).hostname
            company = Company.objects.filter(metadata__shopify_domain=hostname).first()
            if not company:
                company = Company.objects.filter(metadata__metadata__shopify_domain=hostname).first()
            if not company:
                raise Company.DoesNotExist

        except Company.DoesNotExist:
            return Response(
                {'error': f'Company with Shopify domain {hostname} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Retrieve Shopify config from company metadata
        shopify_config = company.metadata.get('shopify_config')
        
        # If shopify_config is not found at the top level, try the double-nested path
        if not shopify_config and isinstance(company.metadata.get('metadata'), dict):
            shopify_config = company.metadata.get('metadata').get('shopify_config')

        # Default to an empty dict if still not found
        shopify_config = shopify_config or {}

        verify_hmac = shopify_config.get('verify_hmac', True) # Default to True for security
        webhook_secret = shopify_config.get('webhook_secret')

        if verify_hmac is True:
            if not webhook_secret:
                logger.error(f"HMAC verification enabled but webhook_secret missing for company {company.id}")
                return Response(
                    {"error": "HMAC verification enabled but secret not configured."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not verify_shopify_webhook(request, webhook_secret):
                logger.warning(f"Invalid Shopify webhook signature received for company {company.id}.")
                return Response(
                    {"error": "Invalid signature"},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            logger.warning(f"HMAC verification skipped for company {company.id} as per configuration.")


        webhook_id = request.headers.get('X-Shopify-Webhook-Id')
        if not webhook_id:
            return Response(
                {'error': 'Missing X-Shopify-Webhook-Id header'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event = Event.objects.create(
                organization=company.organization,
                source='shopify',
                topic='orders/create',
                payload=payload,
                idempotency_key=webhook_id # Re-enabled idempotency
            )
            
            create_erpnext_order_from_shopify_event.delay(event.id)

        except IntegrityError:
            return Response(
                {'message': 'Duplicate webhook received and ignored'},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'message': 'Webhook accepted for processing'},
            status=status.HTTP_202_ACCEPTED
        )