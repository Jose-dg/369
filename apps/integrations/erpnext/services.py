import requests
import logging

logger = logging.getLogger(__name__)

class ERPNextService:
    """
    A service for interacting with the ERPNext API.
    """
    def __init__(self, base_url, api_key, api_secret):
        if not base_url or not api_key or not api_secret:
            raise ValueError("ERPNext base_url, api_key, and api_secret are required.")
        
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, endpoint, data):
        """Helper method to make POST requests."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ERPNext API request failed: {e}")
            if e.response:
                logger.error(f"Response body: {e.response.text}")
            raise

    def create_sales_invoice(self, invoice_data):
        """
        Creates a Sales Invoice in ERPNext.
        
        :param invoice_data: A dictionary representing the Sales Invoice.
        :return: The response from ERPNext.
        """
        return self._post("/api/resource/Sales Invoice", invoice_data)

    def create_customer(self, customer_data):
        """
        Creates a Customer in ERPNext.
        
        :param customer_data: A dictionary representing the Customer.
        :return: The response from ERPNext.
        """
        return self._post("/api/resource/Customer", customer_data)

    def get_customer(self, customer_email):
        """
        Retrieves a customer from ERPNext by email.
        """
        params = {
            'filters': f'[["email_id","=","{customer_email}"]]'
        }
        url = f"{self.base_url}/api/resource/Customer"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            customers = response.json().get('data', [])
            return customers[0] if customers else None
        except requests.exceptions.RequestException as e:
            logger.error(f"ERPNext get_customer request failed: {e}")
            if e.response:
                logger.error(f"Response body: {e.response.text}")
            raise
