# API Specification: ERPNext POS Invoice KPIs

This document outlines the structure of the API endpoint responsible for providing Key Performance Indicators (KPIs) related to Point of Sale (POS) invoices from ERPNext.

## Endpoint

*   **URL:** `/api/integrations/erpnext/pos-invoice-kpis/`
*   **Method:** `GET`
*   **Description:** Retrieves aggregated KPI data for POS invoices. The data can be filtered by a date range.

### Query Parameters

*   `start_date` (string, optional): The start date for the filter range (format: `YYYY-MM-DD`). Defaults to the beginning of the current month.
*   `end_date` (string, optional): The end date for the filter range (format: `YYYY-MM-DD`). Defaults to the current date.

## JSON Response Structure

The API will return a single JSON object containing the following fields.

### 1. Summary (`summary`)

An object containing high-level summaries for the selected period.

```json
"summary": {
  "total_revenue": 15250.75,
  "total_invoices": 350,
  "average_invoice_value": 43.57,
  "total_items_sold": 890
}
```

### 2. Sales Over Time (`sales_over_time`)

An object containing arrays for charting sales trends over the selected period. The `labels` array contains the dates, and the `revenue` and `invoices` arrays contain the corresponding data points.

```json
"sales_over_time": {
  "labels": ["2025-11-01", "2025-11-02", "2025-11-03", ...],
  "revenue": [1200.50, 1500.00, 1350.25, ...],
  "invoices": [25, 30, 28, ...]
}
```

### 3. Top Items (`top_items`)

An array of objects, each representing a top-selling item.

```json
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
]
```

### 4. Payment Methods (`payment_methods`)

An array of objects detailing the breakdown of sales by payment method.

```json
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
]
```

### 5. Recent Invoices (`recent_invoices`)

An array of objects representing the 10 most recent POS invoices.

```json
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
```

## Full Example Response

```json
{
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
```
