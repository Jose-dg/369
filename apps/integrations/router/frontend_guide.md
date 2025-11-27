# Guía de Integración Frontend: Registro Masivo de Pines

Esta guía detalla cómo consumir el endpoint para el registro masivo de pines digitales (Unique Codes) a través del API Gateway.

## Endpoint

**URL:** `/api/integrations/router/unique-codes/register/`
**Método:** `POST`
**Content-Type:** `application/json`

## Estructura del Payload

El endpoint acepta un objeto JSON flexible que permite desde un registro simple de códigos hasta la creación completa de una compra con productos y métodos de pago.

### Campos Principales

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `codes` | Array | **Sí** | Lista de objetos con los pines a registrar. |
| `purchase` | Object | No | Datos de la factura/compra asociada. |
| `purchase_products` | Array | No | Detalles de los productos en la compra (cantidades, costos, etc.). |
| `payment_methods` | Array | No | Métodos de pago utilizados en la compra. |
| `registered_by` | Integer | No | ID del usuario que realiza el registro (opcional si el usuario está autenticado). |

---

### 1. Estructura de `codes` (Array)

Cada objeto en el array `codes` representa un pin individual.

```json
{
  "code": "PIN-12345",           // (String) El código único/pin. Requerido.
  "id": "uuid-del-producto",     // (UUID) ID del producto al que pertenece el pin. Requerido.
  "cost": 10.50,                 // (Decimal) Costo individual del pin. Opcional.
  "state": "available"           // (String) Estado inicial. Default: "available".
}
```

> **Nota:** El campo `id` debe corresponder al `id_product` (UUID) del producto en la base de datos.

---

### 2. Estructura de `purchase` (Object)

Si se envía, crea un registro de compra (Purchase) asociado a los pines.

```json
{
  "purcharse_number": "INV-001", // (String) Número de factura único. Opcional (se genera auto si falta).
  "state": "completed",          // (String) Estado de la compra. Default: "completed".
  "purchase_code": "REF-001",    // (String) Código de referencia interno. Opcional.
  "user": 1                      // (Integer) ID del Cliente (Client ID). Opcional.
}
```

---

### 3. Estructura de `purchase_products` (Array)

Detalle de los productos comprados (útil para inventario).

```json
{
  "id": "uuid-del-producto",     // (UUID) ID del producto. Requerido.
  "quantity": 10,                // (Integer) Cantidad comprada.
  "cost": 10.50,                 // (Decimal) Costo unitario.
  "discount": 0,                 // (Decimal) Descuento aplicado.
  "shipping_cost": 0             // (Decimal) Costo de envío.
}
```

---

### 4. Estructura de `payment_methods` (Array)

Detalle de cómo se pagó la compra.

```json
{
  "payment_method_id": 1,        // (Integer) ID del método de pago. Requerido.
  "amount": 105.00,              // (Decimal) Monto pagado con este método. Requerido.
  "amount_paid": 105.00,         // (Decimal) Monto realmente pagado.
  "payment_code": "TX-123"       // (String) Código de transacción/referencia.
}
```

---

## Ejemplos de Uso

### Caso A: Registro Simple (Solo Pines)
Útil para cargas rápidas de inventario sin asociar a una compra compleja.

```json
{
  "codes": [
    {
      "code": "XBOX-10-ABC",
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "cost": 9.50
    },
    {
      "code": "XBOX-10-DEF",
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "cost": 9.50
    }
  ]
}
```

### Caso B: Registro Completo (Compra + Pines + Pagos)
Útil cuando se registra una compra a un proveedor y se cargan los pines simultáneamente.

```json
{
  "purchase": {
    "purcharse_number": "INV-2023-001",
    "state": "completed"
  },
  "codes": [
    { "code": "PIN-1", "id": "uuid-prod-1", "cost": 10.00 },
    { "code": "PIN-2", "id": "uuid-prod-1", "cost": 10.00 }
  ],
  "purchase_products": [
    {
      "id": "uuid-prod-1",
      "quantity": 2,
      "cost": 10.00
    }
  ],
  "payment_methods": [
    {
      "payment_method_id": 1,
      "amount": 20.00
    }
  ]
}
```

## Respuestas

*   **200 OK / 201 Created**: Éxito. Retorna resumen de creados, existentes y fallidos.
*   **400 Bad Request**: Error de validación (falta código, formato inválido, duplicados en la petición).
*   **500 Internal Server Error**: Error de conexión con el Core Backend o error inesperado.
