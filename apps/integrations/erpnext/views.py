from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class PosInvoiceKpiView(APIView):
    """
    API View to retrieve Key Performance Indicators (KPIs) for POS Invoices from ERPNext.
    """
    def get(self, request, *args, **kwargs):
        """
        Returns a summary of POS invoice data.
        """
        # TODO: Replace this dummy data with actual data from an ERPNext service call.
        # The data structure is based on main/ERPNext_POS_INVOICE_API.md
        
        # Extract query params
        start_date = request.query_params.get('start_date', '2025-11-01')
        end_date = request.query_params.get('end_date', '2025-11-15')

        dummy_data = {
          "summary": {
            "total_revenue": 15250.75,
            "total_invoices": 350,
            "average_invoice_value": 43.57,
            "total_items_sold": 890
          },
          "sales_over_time": {
            "labels": ["2025-11-01", "2025-11-02", "2025-11-03"],
            "revenue": [1200.50, 1500.00, 1350.25],
            "invoices": [25, 30, 28]
          },
          "top_items": [
            {
              "item_name": "Cafe Americano",
              "quantity_sold": 150,
              "total_revenue": 450.00,
              "percentage_of_total_revenue": 2.95
            },
            {
              "item_name": "Croissant",
              "quantity_sold": 120,
              "total_revenue": 360.00,
              "percentage_of_total_revenue": 2.36
            }
          ],
          "payment_methods": [
            {
              "method": "Credit Card",
              "total_revenue": 9500.00,
              "transaction_count": 210,
              "percentage_of_total_revenue": 62.29
            },
            {
              "method": "Cash",
              "total_revenue": 5750.75,
              "transaction_count": 140,
              "percentage_of_total_revenue": 37.71
            }
          ],
          "recent_invoices": [
            {
              "invoice_id": "POS-00350",
              "customer_name": "John Doe",
              "timestamp": "2025-11-15T14:30:00Z",
              "total_amount": 55.25,
              "status": "Paid"
            },
            {
              "invoice_id": "POS-00349",
              "customer_name": "Jane Smith",
              "timestamp": "2025-11-15T14:25:10Z",
              "total_amount": 32.00,
              "status": "Paid"
            }
          ]
        }
        
        return Response(dummy_data, status=status.HTTP_200_OK)
