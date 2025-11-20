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

import json
def _transform_shopify_to_erpnext(shopify_payload, erpnext_customer_name, erpnext_company_name, source_warehouse, default_payment_mode):
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
            "warehouse": source_warehouse,
        })

    if not items:
        logger.error(f"No valid line items with SKUs found. Payload: {json.dumps(shopify_payload)}")
        raise ValueError("No valid line items with SKUs found in Shopify order")

    total_amount = sum(item['amount'] for item in items)

    doc = {
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

    if default_payment_mode:
        doc["payments"] = [
            {
                "mode_of_payment": default_payment_mode,
                "amount": total_amount
            }
        ]
    
    return doc


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

        # Retrieve ERPNext config from company metadata, handling potential nesting
        erpnext_config = company.metadata.get('erpnext_config')
        if not erpnext_config and isinstance(company.metadata.get('metadata'), dict):
            erpnext_config = company.metadata.get('metadata').get('erpnext_config')
        erpnext_config = erpnext_config or {}  # Default to an empty dict if still not found

        # Get source_warehouse from the config
        source_warehouse = erpnext_config.get('source_warehouse')

        # Get default_payment_mode from the config
        default_payment_mode = erpnext_config.get('default_payment_mode')

        # Get the company name for ERPNext from the Company model's name field
        erpnext_company_name = company.name

        missing_config = []
        if not erp_creds.erpnext_site_url: missing_config.append('erpnext_site_url')
        if not erp_creds.api_key: missing_config.append('api_key')
        if not erp_creds.api_secret: missing_config.append('api_secret')
        if not erpnext_company_name: missing_config.append('company_name (Company model)')
        if not source_warehouse: missing_config.append('source_warehouse (metadata)')
        if not default_payment_mode: missing_config.append('default_payment_mode (metadata)')

        if missing_config:
            raise ValueError(f"Missing ERPNext configuration for Company {company.id}: {', '.join(missing_config)}")

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
            source_warehouse,
            default_payment_mode
        )
        
        logger.info(f"Creating Sales Invoice in ERPNext for Shopify order: {event.payload.get('name')}")
        erpnext_response = erp_client.create_document("Sales Invoice", invoice_data)
        
        # Extract the name of the created invoice to submit it
        invoice_name = erpnext_response.get('data', {}).get('name')
        if not invoice_name:
            raise ValueError("ERPNext did not return a name for the created Sales Invoice.")
        
        logger.info(f"Submitting Sales Invoice {invoice_name} in ERPNext.")
        erp_client.submit_document("Sales Invoice", invoice_name)
        
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