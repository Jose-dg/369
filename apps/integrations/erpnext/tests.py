from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.companies.models import Company
from apps.organizations.models import Organization
from apps.events.models import Event
from apps.integrations.erpnext.tasks import create_erpnext_order_from_shopify_event
from apps.integrations.erpnext.models import ErpnextCredential
import json

class ShopifyToErpNextTest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(slug="test-org", uuid="test-uuid")
        self.company = Company.objects.create(
            organization=self.organization,
            name="Test Company",
            metadata={
                "shopify_domain": "test-shop.myshopify.com",
                "erpnext_config": {
                    "source_warehouse": "Stores - TC",
                    "default_payment_mode": "Cash"
                }
            }
        )
        self.credential = ErpnextCredential.objects.create(
            organization=self.organization,
            erpnext_site_url="https://erpnext.example.com",
            api_key="test_key",
            api_secret="test_secret",
            is_active=True
        )

    @patch('apps.integrations.erpnext.tasks.ERPNextClient')
    def test_create_erpnext_order_success(self, MockERPNextClient):
        # Mock ERPNext Client
        mock_client = MockERPNextClient.return_value
        mock_client.get_customer.return_value = {"name": "Test Customer"}
        mock_client.create_document.return_value = {"data": {"name": "SINV-0001"}}
        
        payload = {
            "id": 123456789,
            "name": "#1001",
            "email": "customer@example.com",
            "created_at": "2023-10-27T10:00:00-05:00",
            "currency": "USD",
            "order_status_url": "https://test-shop.myshopify.com/123456/orders/123456789/authenticate?key=123",
            "customer": {
                "id": 987654321,
                "email": "customer@example.com",
                "first_name": "John",
                "last_name": "Doe"
            },
            "line_items": [
                {
                    "id": 111,
                    "title": "Product A",
                    "quantity": 1,
                    "price": "10.00",
                    "sku": "PROD-A"
                }
            ]
        }

        event = Event.objects.create(
            organization=self.organization,
            source='shopify',
            topic='orders/create',
            payload=payload
        )

        create_erpnext_order_from_shopify_event(event.id)

        event.refresh_from_db()
        self.assertEqual(event.status, 'success')
        mock_client.create_document.assert_called()
        
    @patch('apps.integrations.erpnext.tasks.ERPNextClient')
    def test_create_erpnext_order_missing_sku(self, MockERPNextClient):
        # Mock ERPNext Client
        mock_client = MockERPNextClient.return_value
        
        payload = {
            "id": 123456789,
            "name": "#1002",
            "email": "customer@example.com",
            "order_status_url": "https://test-shop.myshopify.com/123456/orders/123456789/authenticate?key=123",
            "customer": {
                "email": "customer@example.com"
            },
            "line_items": [
                {
                    "title": "Product No SKU",
                    "quantity": 1,
                    "price": "10.00",
                    "sku": "" # Missing SKU
                }
            ]
        }

        event = Event.objects.create(
            organization=self.organization,
            source='shopify',
            topic='orders/create',
            payload=payload
        )

        # This should fail or handle gracefully depending on logic
        # Current logic raises ValueError if no items
        try:
            create_erpnext_order_from_shopify_event(event.id)
        except Exception:
            pass

        event.refresh_from_db()
        self.assertEqual(event.status, 'failed')
        self.assertIn("No valid line items", event.error)

