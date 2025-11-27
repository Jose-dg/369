from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import CoreBackendService
import logging

logger = logging.getLogger(__name__)

import copy

class RegisterUniqueCodesView(APIView):
    """
    API Gateway endpoint to proxy requests to the Core Backend RegisterUniqueCodesAPIView.
    """
    
    def post(self, request, *args, **kwargs):
        data = copy.deepcopy(request.data) # Deep copy to ensure mutability and independence
        self._sanitize_payload(data)
        
        print("\n" + "="*60)
        print("🚀 [ROUTER] INCOMING REQUEST FROM FRONTEND")
        print("="*60)
        print(f"Payload received: {data}")
        print(f"Keys present: {list(data.keys())}")
        if 'purchase' in data:
            print(f"Purchase data: {data['purchase']}")
        else:
            print("⚠️ WARNING: No 'purchase' key found in payload!")
        print("="*60 + "\n")
        
        # Optional: Inject current user ID if not provided and user is authenticated
        # if request.user.is_authenticated and 'registered_by' not in data:
        #     data['registered_by'] = request.user.id
            
        service = CoreBackendService()
        
        try:
            result = service.register_unique_codes(data)
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in RegisterUniqueCodesView: {e}")
            # If the service raised an exception that contains the backend response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    return Response(error_data, status=e.response.status_code)
                except ValueError:
                    return Response({"error": str(e)}, status=e.response.status_code)
            
            # Return the actual error message for debugging purposes
            return Response(
                {"error": f"Error connecting to Core Backend: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _sanitize_payload(self, data):
        """
        Sanitizes the payload to avoid backend validation errors.
        Specifically formats 'cost' fields to string with 2 decimal places.
        """
        # Sanitize codes
        if 'codes' in data and isinstance(data['codes'], list):
            for code in data['codes']:
                if isinstance(code, dict) and 'cost' in code:
                    try:
                        # Convert to float first to handle any input type, then format to fixed 2 decimal string
                        val = float(code['cost'])
                        code['cost'] = "{:.2f}".format(val)
                    except (ValueError, TypeError):
                        pass

        # Sanitize purchase_products
        if 'purchase_products' in data and isinstance(data['purchase_products'], list):
            for product in data['purchase_products']:
                if isinstance(product, dict) and 'cost' in product:
                    try:
                        val = float(product['cost'])
                        product['cost'] = "{:.2f}".format(val)
                    except (ValueError, TypeError):
                        pass
