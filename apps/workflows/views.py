from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.workflows.models import WorkflowExecution
from apps.workflows.tasks import transfer_inventory_task, execute_intercompany_transfer_task
from apps.organizations.models import Organization
from apps.companies.models import Company
import logging

logger = logging.getLogger(__name__)

class WebhookReceiverView(APIView):
    def post(self, request, *args, **kwargs):
        document_name = request.data.get('name')
        organization_id = request.data.get('organization_id')

        if not all([document_name, organization_id]):
            return Response(
                {"detail": "Missing 'name' or 'organization_id' field in request data."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            organization = Organization.objects.get(id=organization_id)
            workflow_execution = WorkflowExecution.objects.create(
                organization=organization,
                pr_id_a=document_name,
                status='pending'
            )
            logger.info(f"Created WorkflowExecution {workflow_execution.id} for document {document_name}.")

            transfer_inventory_task.delay(workflow_execution.id)
            logger.info(f"Launched transfer_inventory_task for WorkflowExecution {workflow_execution.id}.")

            return Response(
                {"detail": "Workflow initiated successfully.", "workflow_execution_id": workflow_execution.id},
                status=status.HTTP_200_OK
            )
        except Organization.DoesNotExist:
            return Response(
                {"detail": f"Organization with id '{organization_id}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Error processing webhook for document {document_name}.")
            return Response(
                {"detail": f"An internal server error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class IntercompanyTransferView(APIView):
    def post(self, request, *args, **kwargs):
        # --- 1. Extract data from request ---
        supplier = request.data.get('supplier')
        source_company_id = request.data.get('source_company_id')
        destination_company_id = request.data.get('destination_company_id')
        warehouse = request.data.get('warehouse')
        items_data = request.data.get('items')
        destination_warehouse = request.data.get('destination_warehouse')

        # --- 2. Validate presence of all required top-level fields ---
        required_fields = {
            "supplier": supplier,
            "source_company_id": source_company_id,
            "destination_company_id": destination_company_id,
            "warehouse": warehouse,
            "items": items_data,
            "destination_warehouse": destination_warehouse
        }
        missing_fields = [key for key, value in required_fields.items() if not value]
        if missing_fields:
            return Response(
                {"detail": f"Missing required fields: {', '.join(missing_fields)}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- 3. Validate companies and organization ---
        try:
            source_company = Company.objects.get(id=source_company_id)
            destination_company = Company.objects.get(id=destination_company_id)
        except Company.DoesNotExist:
            return Response(
                {"detail": "Source or destination company not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if source_company.organization != destination_company.organization:
            return Response(
                {"detail": "Source and destination companies must belong to the same organization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        organization = source_company.organization
        
        # --- 4. Validate items_data structure ---
        if not isinstance(items_data, list) or not items_data:
            return Response(
                {"detail": "Field 'items' must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        for i, item in enumerate(items_data):
            if not isinstance(item, dict):
                return Response(
                    {"detail": f"Each item in 'items' must be a dictionary. Error at index {i}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not item.get('item_code'):
                return Response(
                    {"detail": f"Each item must contain a non-empty 'item_code'. Error at index {i}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if 'value_per_unit' not in item or not isinstance(item.get('value_per_unit'), (int, float)):
                return Response(
                    {"detail": f"Each item must contain a numeric 'value_per_unit'. Error at index {i}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(item.get('serial_numbers'), list) or not item.get('serial_numbers'):
                return Response(
                    {"detail": f"Each item must contain a non-empty list of 'serial_numbers'. Error at index {i}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # --- 5. Trigger asynchronous workflow ---
        try:
            execute_intercompany_transfer_task.delay(
                supplier=supplier,
                organization_id=organization.id,
                source_company_id=source_company.id,
                destination_company_id=destination_company.id,
                warehouse=warehouse,
                items_data=items_data,
                destination_warehouse=destination_warehouse
            )

            logger.info(f"Intercompany transfer initiated for organization {organization.id}.")

            return Response(
                {"detail": "Intercompany transfer workflow initiated successfully."},
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.exception(f"Error initiating intercompany transfer for organization {organization.id}.")
            return Response(
                {"detail": f"An internal server error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )