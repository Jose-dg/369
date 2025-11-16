# Integración con la API de SEAGM para Compras

Este documento proporciona una guía sobre cómo conectarse a la API Rest de SEAGM para comprar productos.

## 1. Introducción

La API de SEAGM permite a los desarrolladores integrar las ofertas de productos de SEAGM en sus aplicaciones. Las compras se realizan utilizando Créditos SEAGM. La API utiliza métodos HTTP estándar y devuelve los datos en formato JSON. Para muchas operaciones, la API funciona de forma asíncrona utilizando callbacks para notificar la finalización de la transacción.

Las URLs base para la API son:
-   **Producción:** `https://api.seagm.io`
-   **Sandbox (Pruebas):** `https://sandbox-api.seagm.io`

## 2. Autenticación

La API utiliza un método de autenticación basado en firma para los endpoints seguros (`SIGNED`). Esto implica la creación de una firma HMAC SHA256 para tus solicitudes.

### Credenciales

Necesitarás una **Clave de API (API Key)** y una **Clave Secreta (Secret Key)** para autenticar tus solicitudes.

### Creación de la Firma

Para los endpoints de tipo `SIGNED`, necesitas incluir las siguientes cabeceras en tu solicitud:

-   `X-SEAGM-API-KEY`: Tu Clave de API.
-   `X-SEAGM-API-SIGNATURE`: La firma HMAC SHA256.
-   `X-SEAGM-API-TIMESTAMP`: Una marca de tiempo Unix en milisegundos.

La firma se crea generando un hash HMAC SHA256 de una cadena compuesta por la `timestamp`, el `método` de la solicitud, la `ruta` (`path`) y el `cuerpo` (`body`) de la solicitud (si lo hay), utilizando tu **Clave Secreta**.

**Cadena a firmar:**
```
<timestamp><method><path><body>
```

**Ejemplo (pseudo-código):**
```javascript
const crypto = require('crypto');

const apiKey = 'TU_API_KEY';
const secretKey = 'TU_CLAVE_SECRETA';
const timestamp = Date.now();
const method = 'POST';
const path = '/v1/card-orders';
const body = JSON.stringify({
  "product_code": "product-code",
  "quantity": 1,
  "customer_id": "customer-123"
});

const stringToSign = `${timestamp}${method}${path}${body}`;

const signature = crypto
  .createHmac('sha256', secretKey)
  .update(stringToSign)
  .digest('hex');

// Ahora, realiza la solicitud con las cabeceras requeridas
const headers = {
  'Content-Type': 'application/json',
  'X-SEAGM-API-KEY': apiKey,
  'X-SEAGM-API-SIGNATURE': signature,
  'X-SEAGM-API-TIMESTAMP': timestamp
};
```

## 3. Flujo de Compra General

El flujo general para comprar un producto implica descubrir el producto, crear una orden y manejar el callback.

### Paso 1: Descubrir Productos

Primero, necesitas encontrar el producto que deseas comprar. La API proporciona diferentes endpoints para diferentes tipos de productos.

**Ejemplo: Obtener Categorías de Tarjetas (Cards)**
```http
GET /v1/card-categories
```

**Ejemplo: Obtener Categorías de Recargas (Recharge)**
```http
GET /v1/recharge-categories
```

### Paso 2: Obtener Detalles del Producto

Una vez que tienes la categoría o el tipo, puedes obtener más detalles sobre los productos específicos disponibles.

**Ejemplo: Obtener Detalles de un Tipo de Tarjeta**
```http
GET /v1/card-types/{type_id}
```

### Paso 3: Crear una Orden

Con la información del producto, puedes crear una orden. Esta es una solicitud `POST` al endpoint de órdenes apropiado.

**Ejemplo: Crear una Orden de Tarjeta**
Este es un endpoint `SIGNED`, por lo que requiere autenticación.

```http
POST /v1/card-orders
```

**Cuerpo de la Solicitud (Request Body):**
```json
{
  "product_code": "SEAGM-MY-100",
  "quantity": 1,
  "customer_id": "your-customer-id-123"
}
```

Una solicitud exitosa devolverá un estado `201 Created` con los detalles de la orden, y el estado de la orden será `processing`.

### Paso 4: Manejar el Callback

Dado que muchas operaciones son asíncronas, la API enviará un callback a una URL que configures para notificarte el estado final de la transacción.

El callback contendrá los detalles de la orden y el estado final (`success` o `failed`). Necesitas implementar un "webhook listener" para recibir y procesar estos callbacks.

## 4. Endpoints Importantes para Compras

-   **Ping (Verificar conectividad):** `GET /ping`
-   **Obtener Hora del Servidor (para el timestamp):** `GET /time`
-   **Obtener Detalles de la Cuenta:** `GET /v1/me` (SIGNED)

### Órdenes de Tarjetas (Card Orders)

-   **Categorías:** `GET /v1/card-categories`
-   **Tipos:** `GET /v1/card-types/{type_id}`
-   **Crear Orden:** `POST /v1/card-orders` (SIGNED)
-   **Obtener Órdenes:** `GET /v1/card-orders` (SIGNED)

### Recargas Directas (Direct Top-up)

-   **Categorías:** `GET /v1/recharge-categories`
-   **Tipos:** `GET /v1/recharge-types/{type_id}`
-   **Crear Orden:** `POST /v1/recharge-orders` (SIGNED)
-   **Obtener Órdenes:** `GET /v1/recharge-orders` (SIGNED)

## 5. Manejo de Errores

La API devuelve códigos de estado HTTP estándar. Un estado `2xx` indica éxito, mientras que los estados `4xx` y `5xx` indican errores. El cuerpo de la respuesta para un error contendrá `error_code` y `error_description`.

**Ejemplo de Respuesta de Error:**
```json
{
  "error_code": "INVALID_SIGNATURE",
  "error_description": "The provided signature is invalid."
}
```

Es importante manejar estos errores de forma adecuada en tu aplicación.