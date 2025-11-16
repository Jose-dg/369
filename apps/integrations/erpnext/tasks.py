import logging
from datetime import date
from django.db import transaction
from urllib.parse import urlparse
from core.celery import app
from apps.events.models import Event
from apps.companies.models import Company
from apps.integrations.erpnext.models import ErpnextCredential
from apps.organizations.models import Organization
from apps.workflows.services import ERPNextClient

logger = logging.getLogger(__name__)

def _transform_shopify_to_erpnext(shopify_payload, erpnext_customer_name, erpnext_company_name, default_warehouse):
    """
    Transforms a Shopify order payload into an ERPNext Sales Invoice dictionary.
    """
    if not shopify_payload.get('customer') or not shopify_payload.get('line_items'):
        raise ValueError("Shopify payload is missing customer or line_items")

    items = []
    for item in shopify_payload['line_items']:
        if not item.get('sku'):
            logger.warning(f"Skipping line item without SKU: {item.get('title')}")
            continue
        
        qty = item['quantity']
        rate = float(item['price'])
        
        items.append({
            "item_code": item['sku'],
            "qty": qty,
            "rate": rate,
            "amount": qty * rate,
            "warehouse": default_warehouse,
        })

    if not items:
        raise ValueError("No valid line items with SKUs found in Shopify order")

    return {
        "customer": erpnext_customer_name,
        "company": erpnext_company_name,
        "posting_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "items": items,
        "po_no": shopify_payload.get('name'),
        "update_stock": 1,
        "is_pos": 1,
        "currency": shopify_payload.get('currency', 'USD'),
    }


def _transform_shopify_to_erpnext_customer(shopify_customer_data):
    """
    Transforms a Shopify customer payload into an ERPNext Customer dictionary.
    """
    if not shopify_customer_data or not shopify_customer_data.get('email'):
        raise ValueError("Shopify customer data is missing or does not contain an email.")

    return {
        "customer_name": f"{shopify_customer_data.get('first_name', '')} {shopify_customer_data.get('last_name', '')}".strip(),
        "customer_group": "Individual",
        "customer_type": "Individual",
        "email_id": shopify_customer_data['email'],
    }


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_erpnext_order_from_shopify_event(self, event_id):
    """
    Processes a Shopify order event to create a corresponding Sales Invoice in ERPNext.
    """
    logger.info(f"Starting ERPNext Sales Invoice creation for event_id: {event_id}")

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
        # Extract hostname from order_status_url in the payload
        order_status_url = event.payload.get('order_status_url')
        if not order_status_url:
            raise ValueError("Shopify payload is missing order_status_url for company identification.")
        hostname = urlparse(order_status_url).hostname

        # Find the Company using the hostname, mirroring the view's logic
        company = Company.objects.filter(organization_id=event.organization_id, metadata__shopify_domain=hostname).first()
        if not company:
            company = Company.objects.filter(organization_id=event.organization_id, metadata__metadata__shopify_domain=hostname).first()
        if not company:
            raise Company.DoesNotExist(f"Company with Shopify domain {hostname} not found for organization {event.organization_id}")
        
        # Retrieve ERPNext credentials from ErpnextCredential model
        erp_creds = ErpnextCredential.objects.get(organization=event.organization, is_active=True)

        # Retrieve ERPNext config from company metadata
        erpnext_config = company.metadata.get('erpnext_config', {})
        erpnext_company_name = erpnext_config.get('company_name')
        default_warehouse = erpnext_config.get('default_warehouse')

        if not all([erp_creds.erpnext_site_url, erp_creds.api_key, erp_creds.api_secret, erpnext_company_name, default_warehouse]):
            raise ValueError(f"ERPNext credentials (site_url, api_key, api_secret) or config (company_name, default_warehouse) not fully configured for Company {company.id}")

        erp_client = ERPNextClient(
            api_url=erp_creds.erpnext_site_url,
            api_key=erp_creds.api_key,
            api_secret=erp_creds.api_secret
        )

        shopify_customer = event.payload.get('customer')
        if not shopify_customer or not shopify_customer.get('email'):
            raise ValueError("Customer email not found in Shopify payload.")
        
        customer_email = shopify_customer['email']
        
        # Check if customer exists, if not, create them.
        erpnext_customer_record = erp_client.get_customer(customer_email)
        if not erpnext_customer_record:
            logger.info(f"Customer {customer_email} not found in ERPNext. Creating them.")
            customer_data = _transform_shopify_to_erpnext_customer(shopify_customer)
            erpnext_customer_record = erp_client.create_customer(customer_data)
            # ERPNext create_customer returns a dict with 'name' (the customer ID/name)
            erpnext_customer_name_for_invoice = erpnext_customer_record.get('name')
        else:
            erpnext_customer_name_for_invoice = erpnext_customer_record.get('name')


        invoice_data = _transform_shopify_to_erpnext(
            event.payload,
            erpnext_customer_name_for_invoice,
            erpnext_company_name,
            default_warehouse
        )
        
        logger.info(f"Creating Sales Invoice in ERPNext for Shopify order: {event.payload.get('name')}")
        erpnext_response = erp_client.create_document("Sales Invoice", invoice_data)
        
        event.status = 'success'
        event.response = erpnext_response
        event.save()
        logger.info(f"Successfully processed event {event_id}. ERPNext response: {erpnext_response}")

    except (ErpnextCredential.DoesNotExist, Organization.DoesNotExist, Company.DoesNotExist) as e:
        logger.error(f"Configuration error for event {event_id}: {e}", exc_info=True)
        event.status = 'failed'
        event.error = f"Configuration error: {e}"
        event.save()
        raise # Re-raise to allow Celery to handle retries if configured
    except Exception as e:
        logger.error(f"Failed to process event {event_id}: {str(e)}", exc_info=True)
        event.status = 'failed'
        event.error = str(e)
        event.save()
        # self.retry(exc=e) # Consider retrying for transient API errors