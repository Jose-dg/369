import logging
from celery import shared_task
from apps.workflows.models import WorkflowExecution
from apps.integrations.erpnext.models import ErpnextCredential
from apps.organizations.models import Organization
from apps.workflows.services import ERPNextClient
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(RequestException,), retry_kwargs={'max_retries': 5, 'countdown': 60})
def transfer_inventory_task(self, workflow_execution_id):
    try:
        workflow_execution = WorkflowExecution.objects.get(id=workflow_execution_id)
        workflow_execution.status = 'processing'
        workflow_execution.save()

        logger.info(f"Starting workflow execution {workflow_execution_id} for PR A: {workflow_execution.pr_id_a}")

        company_a_creds = ErpnextCredential.objects.get(organization=workflow_execution.organization, is_active=True)
        company_b_org = Organization.objects.get(name='Company B') # This needs a robust way to be identified
        company_b_creds = ErpnextCredential.objects.get(organization=company_b_org, is_active=True)

        client_a = ERPNextClient(
            api_url=company_a_creds.erpnext_site_url,
            api_key=company_a_creds.api_key,
            api_secret=company_a_creds.api_secret
        )
        client_b = ERPNextClient(
            api_url=company_b_creds.erpnext_site_url,
            api_key=company_b_creds.api_key,
            api_secret=company_b_creds.api_secret
        )

        logger.info(f"Step 1: Reading Purchase Receipt {workflow_execution.pr_id_a} from Company A.")
        pr_a_doc = client_a.get_document("Purchase Receipt", workflow_execution.pr_id_a)
        serial_nos = client_a.get_serial_nos_from_purchase_receipt(workflow_execution.pr_id_a)
        logger.info(f"Extracted serial numbers: {serial_nos}")

        logger.info(f"Step 2: Creating Delivery Note in Company A for PR {workflow_execution.pr_id_a}.")
        dn_a_data = { "doctype": "Delivery Note", "customer": pr_a_doc["data"]["supplier"], "set_warehouse": pr_a_doc["data"]["set_warehouse"], "items": [] }
        for item_data in pr_a_doc["data"]["items"]:
            dn_a_data["items"].append({ "item_code": item_data["item_code"], "qty": item_data["qty"], "serial_no": "\n".join(serial_nos), "warehouse": item_data["warehouse"] })
        
        dn_a_response = client_a.create_document("Delivery Note", dn_a_data)
        dn_a_name = dn_a_response["data"]["name"]
        client_a.submit_document("Delivery Note", dn_a_name)
        workflow_execution.dn_id_a = dn_a_name
        workflow_execution.save()
        logger.info(f"Delivery Note {dn_a_name} created and submitted in Company A.")

        logger.info(f"Step 3: Creating Purchase Receipt in Company B with serials: {serial_nos}.")
        pr_b_data = { "doctype": "Purchase Receipt", "supplier": pr_a_doc["data"]["supplier"], "set_warehouse": "Default Warehouse - B", "items": [] }
        for item_data in pr_a_doc["data"]["items"]:
            pr_b_data["items"].append({ "item_code": item_data["item_code"], "qty": item_data["qty"], "serial_no": "\n".join(serial_nos), "warehouse": "Default Warehouse - B" })
        
        pr_b_response = client_b.create_document("Purchase Receipt", pr_b_data)
        pr_b_name = pr_b_response["data"]["name"]
        client_b.submit_document("Purchase Receipt", pr_b_name)
        workflow_execution.pr_id_b = pr_b_name
        workflow_execution.status = 'success'
        workflow_execution.save()
        logger.info(f"Purchase Receipt {pr_b_name} created in Company B. Workflow completed.")

    except (ErpnextCredential.DoesNotExist, Organization.DoesNotExist) as e:
        workflow_execution.error_message = "ERPNext credential or Organization configuration not found."
        workflow_execution.status = 'failed'
        workflow_execution.save()
        logger.error(workflow_execution.error_message)
        raise
    except RequestException as e:
        workflow_execution.error_message = f"API request failed: {e}"
        workflow_execution.status = 'failed'
        workflow_execution.save()
        logger.error(workflow_execution.error_message)
        raise self.retry(exc=e)
    except Exception as e:
        workflow_execution.error_message = f"An unexpected error occurred: {e}"
        workflow_execution.status = 'failed'
        workflow_execution.save()
        logger.error(workflow_execution.error_message)
        raise

from requests.exceptions import RequestException, HTTPError
from apps.companies.models import Company

@shared_task(bind=True)
def execute_intercompany_transfer_task(self, supplier, organization_id, source_company_id, destination_company_id, warehouse, items_data, destination_warehouse):
    try:
        logger.info(f"Starting intercompany transfer for organization {organization_id}.")
        
        organization = Organization.objects.get(id=organization_id)
        source_company = Company.objects.get(id=source_company_id)
        destination_company = Company.objects.get(id=destination_company_id)
        
        credentials = ErpnextCredential.objects.get(organization=organization, is_active=True)
        erp_client = ERPNextClient(api_url=credentials.erpnext_site_url, api_key=credentials.api_key, api_secret=credentials.api_secret)

        # Step 1: Create Purchase Receipt in Source Company (from external supplier)
        logger.info(f"Step 1: Creating Purchase Receipt in {source_company.name} from supplier {supplier}.")
        pr_source_items = []
        for item in items_data:
            pr_source_items.append({
                "item_code": item['item_code'],
                "qty": len(item['serial_numbers']),
                "rate": item['value_per_unit'],
                "warehouse": warehouse,
                "serial_no": "\n".join(item['serial_numbers'])
            })
        
        pr_source_data = {
            "doctype": "Purchase Receipt",
            "company": source_company.name,
            "supplier": supplier,
            "set_warehouse": warehouse,
            "items": pr_source_items
        }
        pr_source_response = erp_client.create_document("Purchase Receipt", pr_source_data)
        pr_source_name = pr_source_response["data"]["name"]
        erp_client.submit_document("Purchase Receipt", pr_source_name)
        logger.info(f"Purchase Receipt {pr_source_name} created in {source_company.name}.")

        # Step 2: Create Delivery Note from Source Company to Destination Company
        logger.info(f"Step 2: Creating Delivery Note from {source_company.name} to {destination_company.name}.")
        dn_items = []
        for item in items_data:
            dn_items.append({
                "item_code": item['item_code'],
                "qty": len(item['serial_numbers']),
                "rate": item['value_per_unit'],
                "warehouse": warehouse,
                "serial_no": "\n".join(item['serial_numbers'])
            })

        # Get ERPNext customer name from metadata, fallback to company name
        customer_metadata = destination_company.metadata
        if 'metadata' in customer_metadata: # Handle potential extra nesting
            customer_metadata = customer_metadata['metadata']
        erpnext_customer_name = customer_metadata.get('erpnext_config', {}).get('erpnext_customer_name', destination_company.name)
        logger.info(f"Using customer name for Delivery Note: '{erpnext_customer_name}'")

        dn_data = {
            "doctype": "Delivery Note",
            "company": source_company.name,
            "customer": erpnext_customer_name,
            "set_warehouse": warehouse,
            "items": dn_items
        }
        dn_response = erp_client.create_document("Delivery Note", dn_data)
        dn_name = dn_response["data"]["name"]
        erp_client.submit_document("Delivery Note", dn_name)
        logger.info(f"Delivery Note {dn_name} created in {source_company.name}.")

        # Step 3: Create Purchase Receipt in Destination Company (from source company)
        logger.info(f"Step 3: Creating Purchase Receipt in {destination_company.name}.")
        pr_dest_items = []
        for item in items_data:
            pr_dest_items.append({
                "item_code": item['item_code'],
                "qty": len(item['serial_numbers']),
                "rate": item['value_per_unit'],
                "warehouse": destination_warehouse,
                "serial_no": "\n".join(item['serial_numbers'])
            })

        pr_dest_data = {
            "doctype": "Purchase Receipt",
            "company": destination_company.name,
            "supplier": source_company.name,
            "set_warehouse": destination_warehouse,
            "items": pr_dest_items
        }
        pr_dest_response = erp_client.create_document("Purchase Receipt", pr_dest_data)
        pr_dest_name = pr_dest_response["data"]["name"]
        erp_client.submit_document("Purchase Receipt", pr_dest_name)
        logger.info(f"Purchase Receipt {pr_dest_name} created in {destination_company.name}.")

        logger.info("Intercompany transfer workflow completed successfully.")

    except (ErpnextCredential.DoesNotExist, Organization.DoesNotExist, Company.DoesNotExist) as e:
        logger.error(f"Configuration error in intercompany transfer workflow: {e}")
        # Do not retry for configuration errors
        raise

    except HTTPError as e:
        # For HTTP errors, check the status code to decide whether to retry.
        if e.response and 400 <= e.response.status_code < 500:
            # 4xx errors are client errors (bad data). Do not retry.
            logger.error(f"Permanent API client error: {e.response.status_code} - {e.response.text}")
            raise
        else:
            # 5xx errors are server errors. Retry these.
            logger.warning(f"API server error, retrying: {e}")
            raise self.retry(exc=e, max_retries=5, countdown=60)

    except RequestException as e:
        # For other network errors (timeouts, connection errors), retry.
        logger.warning(f"Network error, retrying: {e}")
        raise self.retry(exc=e, max_retries=5, countdown=60)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        # Do not retry for other unexpected errors.
        raise
