import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class CoreBackendService:
    """
    Service for interacting with the specialized Core Backend.
    """
    def __init__(self):
        # TODO: Revert to settings after testing
        # self.base_url = getattr(settings, 'CORE_BACKEND_URL', 'http://localhost:8001') 
        self.base_url = "https://diem.onrender.com/"
        self.api_key = getattr(settings, 'CORE_BACKEND_API_KEY', '')
        
        self.headers = {
            "Content-Type": "application/json",
            # Add authentication headers if required, e.g.:
            # "Authorization": f"Bearer {self.api_key}",
        }

    def register_unique_codes(self, data):
        """
        Sends a request to the RegisterUniqueCodesAPIView endpoint.
        
        :param data: Dictionary containing 'codes', 'purchase', etc.
        :return: JSON response from the backend.
        """
        endpoint = "api/bulk/" # Adjusted endpoint path
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"📡 [ROUTER] SENDING TO CORE BACKEND: {url}")
            print(f"Payload outgoing: {data}")
            logger.info(f"Sending bulk register request to {url}")
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            
            response_data = response.json()
            print(f"📥 [ROUTER] RESPONSE FROM CORE BACKEND:")
            print(f"{response_data}")
            
            return response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Core Backend API request failed: {e}")
            if e.response is not None:
                logger.error(f"Response body: {e.response.text}")
                # Return the error response from the backend if available
                try:
                    return e.response.json()
                except ValueError:
                    pass
            raise
