# Integración del Frontend para el Workflow de Transferencia Intercompañía

Este documento describe cómo integrar una interfaz de frontend, preferiblemente construida con Next.js y `shadcn/ui`, con el endpoint de la API para iniciar el flujo de trabajo de transferencia de inventario entre compañías.

## 1. Detalles de la Petición (Request)

Para iniciar el flujo de trabajo, se debe realizar una petición `POST` al siguiente endpoint:

- **URL:** `http://localhost:8000/api/workflow/intercompany-transfer/`
- **Método:** `POST`
- **Headers:**
  - `Content-Type: application/json`

### Cuerpo de la Petición (Body)

El cuerpo de la petición debe ser un objeto JSON con la siguiente estructura:

| Campo                      | Tipo                               | Descripción                                                                                             |
| -------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `supplier`                 | `string`                           | Nombre del proveedor externo original de los productos.                                                 |
| `source_company_id`        | `string` (UUID)                    | El ID de la compañía que origina la transferencia.                                                      |
| `destination_company_id`   | `string` (UUID)                    | El ID de la compañía que recibirá los productos.                                                        |
| `warehouse`                | `string`                           | Nombre de la bodega de origen desde donde salen los productos.                                          |
| `items`                    | `Array` de `Objetos`               | Una lista de los productos a transferir. Ver la estructura del objeto `item` a continuación.            |
| `destination_warehouse`    | `string`                           | Nombre de la bodega de destino donde llegarán los productos.                                            |

#### Estructura del Objeto `item`

Cada objeto dentro del array `items` debe tener la siguiente estructura:

| Campo            | Tipo                | Descripción                                                                |
| ---------------- | ------------------- | -------------------------------------------------------------------------- |
| `item_code`      | `string`            | El código (SKU) del producto en ERPNext.                                   |
| `value_per_unit` | `number`            | El costo o valor por unidad del producto.                                  |
| `serial_numbers` | `Array` de `string` | Una lista con los números de serie únicos para la cantidad de ese producto. |

### Ejemplo de Código (usando `fetch` en TypeScript)

```typescript
async function startIntercompanyTransfer(transferData: any) {
  try {
    const response = await fetch('http://localhost:8000/api/workflow/intercompany-transfer/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Aquí irían otros headers, como el de autenticación (Authorization)
      },
      body: JSON.stringify(transferData),
    });

    if (response.status === 202) {
      // La tarea fue aceptada y se está procesando en segundo plano.
      console.log('Transferencia iniciada con éxito.');
      // Mostrar un toast/notificación de éxito.
    } else {
      // Manejar errores de validación (4xx) o de servidor (5xx)
      const errorData = await response.json();
      console.error('Error al iniciar la transferencia:', errorData);
      // Mostrar errores al usuario.
    }
  } catch (error) {
    console.error('Error de red o de conexión:', error);
    // Mostrar un error genérico.
  }
}

// Ejemplo de datos a enviar:
const data = {
  "supplier": "Proveedor Principal",
  "source_company_id": "97e3d8ad-8376-454a-9133-5d13c7a7af85",
  "destination_company_id": "480c01d8-0dd6-4c76-8c8f-becf5760db38",
  "warehouse": "Bodega Principal - M4G",
  "items": [
    {
      "item_code": "PROD-001",
      "value_per_unit": 150.75,
      "serial_numbers": ["SN-UNIQUE-001", "SN-UNIQUE-002"]
    }
  ],
  "destination_warehouse": "Bodega Destino - DM"
};

startIntercompanyTransfer(data);
```

## 2. Diseño de Interfaz (UI) con `shadcn/ui`

Se recomienda una interfaz minimalista y moderna, centrada en la usabilidad.

- **Contenedor Principal:** Usar un componente `<Card>` para agrupar todo el formulario.
- **Campos de Texto:** Usar `<Input>` para `supplier`, `warehouse` y `destination_warehouse`.
- **Selección de Compañías:** Para `source_company_id` y `destination_company_id`, es crucial usar un `<Select>` o `<Combobox>`. Estos campos **no deben ser de texto libre**. Se necesitarán endpoints adicionales en el backend para obtener la lista de compañías disponibles (ej. `GET /api/companies/`).
- **Gestión de Items (la parte más compleja):**
  - Implementar una lista dinámica.
  - Un botón `<Button>` "Añadir Producto" para agregar un nuevo objeto al array `items`.
  - Cada producto en la lista puede ser una "sub-tarjeta" (`<Card>`) con:
    - Un `<Input>` para `item_code`.
    - Un `<Input type="number">` para `value_per_unit`.
    - Un `<Textarea>` para `serial_numbers`, instruyendo al usuario a que ingrese un número de serie por línea. El frontend deberá procesar este texto para convertirlo en un array de strings.
    - Un botón de "Eliminar" (`<Button variant="destructive">`) para quitar ese producto de la lista.
- **Botón de Envío:** Un `<Button>` principal para enviar el formulario.

## 3. Consideraciones Adicionales Importantes

Estos son aspectos clave que no se deben pasar por alto durante el desarrollo del frontend:

#### a. Manejo de Estado (State Management)
El estado del formulario, especialmente la lista dinámica de `items`, puede volverse complejo.
- Para un formulario como este, `useState` puede ser insuficiente. Se recomienda usar una librería de manejo de formularios como **React Hook Form** o, en su defecto, `useReducer` para gestionar el estado de forma más predecible y escalable.

#### b. Obtención de Datos para Selects/Combobox
Como se mencionó, el usuario no debería escribir los IDs de las compañías a mano. El frontend necesitará consumir endpoints `GET` para poblar estos selectores.
- `GET /api/companies/` para obtener las compañías.
- `GET /api/warehouses/` (si aplica) para obtener las bodegas.
- Se recomienda usar una librería de fetching como **SWR** o **React Query (TanStack Query)** para manejar el cache, revalidación y estado de carga de estos datos.

#### c. Experiencia de Usuario (UX) y Manejo de Asincronía
- **Feedback de Carga:** Mientras la petición se está enviando, el botón de "Enviar" debe ser deshabilitado y mostrar un spinner (`<Loader2 className="mr-2 h-4 w-4 animate-spin" />`).
- **Respuesta Asíncrona (202 Accepted):** El backend responde inmediatamente con un `202 Accepted`, lo que significa "He recibido tu petición y la voy a procesar". **No significa que ya terminó**. El frontend no debe hacer esperar al usuario.
  - **Acción recomendada:** Al recibir un `202`, muestra una notificación de éxito (un "Toast" con `<Toaster />` de shadcn) diciendo "Transferencia iniciada correctamente" y limpia el formulario para que el usuario pueda realizar otra.
- **Visualización de Estado (Opcional pero recomendado):** Considera crear una vista separada en la aplicación donde el usuario pueda ver el historial de transferencias y su estado (`pendiente`, `procesando`, `éxito`, `fallido`). Esto requeriría un nuevo endpoint en el backend (ej. `GET /api/workflow/executions/`).

#### d. Manejo de Errores
- **Errores de Validación (4xx):** Si el backend devuelve un error de validación (ej. "Falta el campo X"), el frontend debe mostrar el mensaje de error junto al campo correspondiente.
- **Errores de Servidor (5xx):** Para errores inesperados del servidor o de red, muestra un Toast genérico de error: "Ocurrió un error inesperado. Por favor, inténtalo de nuevo."
