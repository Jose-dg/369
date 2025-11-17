# API Documentation: Intercompany Transfer

This document provides instructions on how to use the Intercompany Transfer API endpoint to initiate a workflow for transferring inventory between two companies within the same organization.

## Endpoint

- **URL:** `/api/workflows/intercompany-transfer/`
- **HTTP Method:** `POST`

## Headers

| Header                | Description                                                                                                  | Example                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------ |
| `Authorization`       | A valid JWT token for authentication.                                                                        | `Bearer <your_jwt_token>`      |
| `X-Organization-Slug` | The unique slug of the organization under which the transfer is being made. This is **required** for tenancy. | `three69-u825`                 |
| `Content-Type`        | Specifies the media type of the resource.                                                                    | `application/json`             |

## Request Body

The request body must be a JSON object containing the details of the transfer.

### Structure

```json
{
    "supplier": "string",
    "source_company_id": "uuid",
    "destination_company_id": "uuid",
    "warehouse": "string",
    "items": [
        {
            "item_code": "string",
            "value_per_unit": "number",
            "serial_numbers": ["string"]
        }
    ],
    "destination_warehouse": "string"
}
```

### Field Descriptions

- `supplier` (string, required): The name or identifier of the supplier.
- `source_company_id` (string, required): The UUID of the company from which the inventory is being sent.
- `destination_company_id` (string, required): The UUID of the company that is receiving the inventory.
- `warehouse` (string, required): The identifier of the source warehouse.
- `items` (array, required): A list of items to be transferred.
  - `item_code` (string, required): The unique code of the item.
  - `value_per_unit` (number, required): The monetary value of a single unit of the item.
  - `serial_numbers` (array of strings, required): A non-empty list of serial numbers for the units being transferred.
- `destination_warehouse` (string, required): The identifier of the destination warehouse where the inventory will be received.

### Example Payload

```json
{
    "supplier": "Main Supplier Inc.",
    "source_company_id": "97e3d8ad-8376-454a-9133-5d13c7a7af85",
    "destination_company_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "warehouse": "WH-Primary",
    "items": [
        {
            "item_code": "LAP-MAC-M3-PRO",
            "value_per_unit": 1999.99,
            "serial_numbers": ["SN-1001", "SN-1002"]
        },
        {
            "item_code": "MON-DELL-27-4K",
            "value_per_unit": 499.50,
            "serial_numbers": ["SN-2001", "SN-2002", "SN-2003"]
        }
    ],
    "destination_warehouse": "WH-Secondary"
}
```

## Responses

### Success Response

- **Status Code:** `202 Accepted`
- **Description:** The request was successfully received and the asynchronous transfer workflow has been initiated.
- **Body:**

  ```json
  {
      "detail": "Intercompany transfer workflow initiated successfully."
  }
  ```

### Error Responses

- **Status Code:** `400 Bad Request`
  - **Description:** The request is missing required fields or the data is malformed (e.g., `items` is not a list).
  - **Body Example:**
    ```json
    {
        "detail": "Missing required fields: supplier, destination_warehouse."
    }
    ```

- **Status Code:** `401 Unauthorized`
  - **Description:** The `Authorization` header is missing or the JWT token is invalid.

- **Status Code:** `404 Not Found`
  - **Description:** The `source_company_id` or `destination_company_id` does not correspond to an existing company.
  - **Body:**
    ```json
    {
        "detail": "Source or destination company not found."
    }
    ```
