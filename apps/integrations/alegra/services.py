import requests
import logging
import json
from .models import AlegraCredential, AlegraInvoice, Company
from apps.events.models import Event

logger = logging.getLogger(__name__)

ALEGRA_API_BASE_URL = "https://api.alegra.com/api/v1/"

def _get_alegra_auth(credential: AlegraCredential):
    """Returns the authentication tuple for Alegra API requests."""
    return (credential.api_key, credential.api_secret)

def _get_next_invoice_number(credential: AlegraCredential, template_id: int) -> int:
    """
    Fetches the next available invoice number for a given number template.
    """
    if not template_id:
        raise ValueError("Alegra Number Template ID is not configured in company metadata.")

    auth = _get_alegra_auth(credential)
    headers = {"Accept": "application/json"}
    url = f"{ALEGRA_API_BASE_URL}number-templates/{template_id}"
    
    logger.info(f"Fetching next invoice number for template ID: {template_id}")
    response = requests.get(url, auth=auth, headers=headers, timeout=10)
    response.raise_for_status()
    
    template_data = response.json()
    next_number = template_data.get('next' if 'next' in template_data else 'nextInvoiceNumber')
    if not next_number:
        raise ValueError(f"Could not determine next invoice number from Alegra's response for template {template_id}")

    logger.info(f"Got next invoice number: {next_number}")
    return next_number

def find_or_create_alegra_contact(credential: AlegraCredential, customer_payload: dict) -> int:
    """
    Finds a contact in Alegra by identification number. If not found, creates it.
    Returns the Alegra contact ID.
    """
    if not customer_payload or not customer_payload.get('identification'):
        raise ValueError("Customer identification data is missing from payload.")

    identification_number = customer_payload['identification']
    auth = _get_alegra_auth(credential)
    headers = {"Accept": "application/json"}
    search_url = f"{ALEGRA_API_BASE_URL}contacts?identification={identification_number}"

    logger.info(f"Searching for Alegra contact with identification: {identification_number}")
    response = requests.get(search_url, auth=auth, headers=headers, timeout=10)
    response.raise_for_status()
    
    results = response.json()
    if results and isinstance(results, list):
        contact_id = results[0]['id']
        logger.info(f"Found existing Alegra contact. ID: {contact_id}")
        return contact_id

    logger.info("Alegra contact not found. Creating new contact.")
    create_url = f"{ALEGRA_API_BASE_URL}contacts"
    
    contact_payload = {
        "name": customer_payload.get('name'),
        "identificationObject": {
            "type": customer_payload.get('identification_type', 'NIT'),
            "number": identification_number
        },
        "email": customer_payload.get('email'),
        "mobile": customer_payload.get('phone'),
        "address": {
            "city": customer_payload.get('address', {}).get('city'),
            "address": customer_payload.get('address', {}).get('line1')
        },
        "type": "client"
    }

    print(f"\n--- Alegra Contact Payload ---")
    print(json.dumps(contact_payload, indent=2))
    print(f"------------------------------\n")

    response = requests.post(create_url, auth=auth, headers=headers, json=contact_payload, timeout=15)
    response.raise_for_status()
    new_contact = response.json()

    print(f"\n--- Alegra Contact Response ---")
    print(json.dumps(new_contact, indent=2))
    print(f"-------------------------------\n")
    
    new_contact_id = new_contact['id']
    logger.info(f"Successfully created new Alegra contact. ID: {new_contact_id}")
    
    return new_contact_id

def create_alegra_invoice(credential: AlegraCredential, event_payload: dict, alegra_contact_id: int, company_metadata: dict) -> tuple[dict, dict]:
    """
    Creates an invoice in Alegra using the transformed payload from an event.
    Returns a tuple containing the Alegra API response and the payload that was sent.
    """
    auth = _get_alegra_auth(credential)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    invoice_url = f"{ALEGRA_API_BASE_URL}invoices"

    # --- Get Alegra-specific config from its own namespace in metadata ---
    alegra_config = company_metadata.get("metadata", {}).get("alegra_config", {})
    template_id = alegra_config.get("number_template_id")
    template_prefix = alegra_config.get("number_template_prefix", "")
    payment_mappings = alegra_config.get("payment_method_mappings", {})
    default_bank_id = alegra_config.get("default_bank_id", 1)

    # --- Get Next Invoice Number ---
    next_invoice_number = _get_next_invoice_number(credential, template_id)

    # --- Transform items using the new direct alegra_product_id ---
    items_payload = [
        {
            "id": item.get('alegra_product_id'),
            "price": item.get('rate'),
            "quantity": item.get('qty'),
        }
        for item in event_payload.get("items", [])
    ]
    # Filter out items that don't have an alegra_product_id
    items_payload = [item for item in items_payload if item['id'] is not None]
    if not items_payload:
        raise ValueError("No valid items with an 'alegra_product_id' found in payload.")

    # --- Transform payments using new business logic for bank IDs ---
    def _get_bank_id(mode_of_payment: str) -> int:
        if mode_of_payment == "Bancolombia":
            return 5
        if mode_of_payment == "Davivienda":
            return 6
        if mode_of_payment == "BBVA":
            return 8
        if mode_of_payment == "Tarjeta de Crédito":
            return 2
        # Fallback to the mappings in metadata or the absolute default
        return payment_mappings.get(mode_of_payment, default_bank_id)

    payments_payload = [
        {
            "account": {"id": str(_get_bank_id(payment.get('mode_of_payment')))}, # Convert bank_id to string
            "date": event_payload.get('posting_date'),
            "amount": payment.get('amount'),
            "paymentMethod": "transfer"  # Use hardcoded 'transfer' as per working example
        }
        for payment in event_payload.get("payments", [])
    ]

    # --- Build Final Payload (more complete version) ---
    invoice_payload = {
        "numberTemplate": {
            "id": template_id, 
            "prefix": template_prefix,
            "number": next_invoice_number
        },
        "date": event_payload.get('posting_date'),
        "dueDate": event_payload.get('due_date', event_payload.get('posting_date')),
        "client": {"id": int(alegra_contact_id)},
        "items": items_payload,
        "payments": payments_payload,
        "stamp": {"generateStamp": True}, 
        "observations": f"Invoice from ERPNext POS: {event_payload.get('name')}",
        "status": "open",
        "paymentForm": "CASH",
        "paymentMethod": "CASH",
        "type": "NATIONAL",
        "operationType": "STANDARD"
    }

    print(f"\n--- Alegra Invoice Payload ---")
    print(json.dumps(invoice_payload, indent=2))
    print(f"------------------------------\n")

    logger.info(f"Sending new invoice to Alegra for contact ID: {alegra_contact_id}")
    try:
        response = requests.post(invoice_url, auth=auth, headers=headers, json=invoice_payload, timeout=20)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("\n--- Alegra API Error Response ---")
        try:
            print(json.dumps(e.response.json(), indent=2))
        except json.JSONDecodeError:
            print(e.response.text)
        print("-----------------------------------\n")
        raise e

    alegra_response = response.json()

    print(f"\n--- Alegra Invoice Response ---")
    print(json.dumps(alegra_response, indent=2))
    print(f"-------------------------------\n")

    logger.info("Successfully created Alegra invoice.")
    return alegra_response, invoice_payload

def send_invoice_from_event(event: Event):
    """
    Orchestrator function that processes an event and sends the invoice to Alegra.
    """
    logger.info(f"Starting to process event {event.id} for Alegra integration.")
    payload = event.payload
    
    # 1. Get credentials and company metadata
    try:
        company = Company.objects.get(organization=event.organization, name__iexact=payload.get('company'))
        credential = AlegraCredential.objects.get(company=company, is_active=True)
    except (Company.DoesNotExist, AlegraCredential.DoesNotExist) as e:
        raise ValueError(f"Active Alegra credentials not found for company specified in event. Error: {e}")

    # 2. Find or create contact
    alegra_contact_id = find_or_create_alegra_contact(credential, payload.get('customer'))

    # 3. Create invoice, passing metadata for configuration
    alegra_response, invoice_payload = create_alegra_invoice(credential, payload, alegra_contact_id, company.metadata)

    # 4. Log the transaction for auditing
    AlegraInvoice.objects.create(
        company=company,
        event=event,
        alegra_id=alegra_response.get('id'),
        status=alegra_response.get('status'),
        payload_sent=invoice_payload,
        response_received=alegra_response
    )
    logger.info(f"Alegra transaction logged for event {event.id}")

    return alegra_response