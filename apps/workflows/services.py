import requests
import json

class ERPNextClient:
    def __init__(self, api_url, api_key, api_secret):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(self, method, path, data=None):
        url = f"{self.api_url}/api/resource/{path}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, data=json.dumps(data))
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, data=json.dumps(data))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {response.text}")
            raise
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            raise
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected error occurred: {req_err}")
            raise

    def get_document(self, doctype, name):
        path = f"{doctype}/{name}"
        return self._make_request("GET", path)

    def create_document(self, doctype, data):
        path = doctype
        return self._make_request("POST", path, data)

    def get_customer(self, customer_email):
        """
        Retrieves a customer from ERPNext by email.
        """
        params = {
            'filters': json.dumps([["email_id", "=", customer_email]])
        }
        # ERPNext GET request for a list of documents uses /api/resource/{doctype}
        # with filters in params.
        url = f"{self.api_url}/api/resource/Customer"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            customers = response.json().get('data', [])
            return customers[0] if customers else None
        except requests.exceptions.RequestException as e:
            print(f"ERPNext get_customer request failed: {e}")
            if e.response:
                print(f"Response body: {e.response.text}")
            raise

    def create_customer(self, customer_data):
        """
        Creates a Customer in ERPNext.
        
        :param customer_data: A dictionary representing the Customer.
        :return: The response from ERPNext.
        """
        return self.create_document("Customer", customer_data)

    def submit_document(self, doctype, name):
        path = f"{doctype}/{name}"
        return self._make_request("PUT", path, {"docstatus": 1}) # 1 for submitted

    def get_serial_nos_from_purchase_receipt(self, pr_name):
        # This is a specific method to get serial numbers from a Purchase Receipt
        # It might require a custom API call or parsing the PR document
        # For now, let's assume we can get it from the document itself
        pr_doc = self.get_document("Purchase Receipt", pr_name)
        serial_nos = []
        for item in pr_doc.get('data', {}).get('items', []):
            if item.get('has_serial_no') and item.get('serial_no'):
                serial_nos.extend(item['serial_no'].split('\n'))
        return [sn.strip() for sn in serial_nos if sn.strip()]
