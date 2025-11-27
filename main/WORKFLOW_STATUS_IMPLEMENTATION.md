# Plan de Implementación: Sistema de Seguimiento de Estado para Workflows

## 1. Problema

Actualmente, los flujos de trabajo asíncronos (tareas de Celery) se inician desde la API, la cual responde inmediatamente con un `202 ACCEPTED`. Si ocurre un error de negocio durante la ejecución de la tarea en segundo plano (ej: SKU no encontrado, serial duplicado), el cliente que originó la llamada nunca es notificado del fallo específico, ya que la conexión HTTP original ya se ha cerrado.

Esto resulta en una falta de feedback y dificulta la depuración y la comunicación del estado al usuario final.

## 2. Solución Propuesta

Se implementará un sistema de seguimiento de estado por pasos para cada ejecución de un workflow. Esto permitirá al cliente (frontend) consultar el progreso detallado de una tarea asíncrona, incluyendo el estado de cada paso intermedio y cualquier error que pueda ocurrir.

El flujo será el siguiente:
1.  El cliente envía la petición a la API para iniciar un workflow.
2.  La API crea un registro de `WorkflowExecution` en la base de datos, inicializando una estructura de pasos, y responde inmediatamente con el ID de dicha ejecución.
3.  La tarea de Celery se ejecuta en segundo plano, actualizando el estado de cada paso en el registro de `WorkflowExecution` a medida que avanza.
4.  El cliente utiliza el ID de la ejecución para consultar un nuevo endpoint de estado (`/api/workflows/executions/<id>/`) periódicamente (polling) y obtener la información actualizada para mostrarla al usuario (ej: una barra de progreso, una lista de pasos, o un mensaje de error).

## 3. Detalles de Implementación

### 3.1. Modelo `apps.workflows.models.WorkflowExecution`

Se modificará el modelo para que sea la fuente de verdad del estado de la ejecución.

**Campos a añadir/modificar:**
- `status`: `CharField` para el estado general. Opciones: `pending`, `in_progress`, `completed`, `failed`.
- `steps`: `JSONField` para almacenar la estructura de los pasos del workflow.
- `error_detail`: `TextField` para almacenar un mensaje claro y legible si la ejecución falla.
- `result`: `JSONField` para guardar cualquier dato resultante de la ejecución exitosa.

**Ejemplo de la estructura del campo `steps`:**
```json
{
  "total_steps": 3,
  "current_step_number": 1,
  "step_list": [
    {
      "name": "Creando 'Purchase Receipt' en origen",
      "status": "in_progress",
      "started_at": "2025-11-18T19:30:00Z",
      "completed_at": null,
      "error": null
    },
    {
      "name": "Creando 'Delivery Note' desde origen",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "error": null
    },
    {
      "name": "Creando 'Purchase Receipt' en destino",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "error": null
    }
  ]
}
```

### 3.2. Vista Principal (`apps.workflows.views.IntercompanyTransferView`)

- **Responsabilidad:** Iniciar el `WorkflowExecution`.
- **Lógica:**
    1. Al recibir una petición `POST` válida, crea una instancia de `WorkflowExecution`.
    2. Define e inicializa la estructura de `steps` para el workflow específico, con todos los pasos en estado `pending`.
    3. Llama a la tarea de Celery (`execute_intercompany_transfer_task.delay()`) pasándole el `id` de la instancia recién creada.
    4. Responde con `202 ACCEPTED` y el `id` de la ejecución.

### 3.3. Tarea de Celery (`apps.workflows.tasks.execute_intercompany_transfer_task`)

- **Responsabilidad:** Ejecutar la lógica de negocio y actualizar el estado.
- **Lógica:**
    1. Recibe el `workflow_execution_id`.
    2. Obtiene el objeto `WorkflowExecution` de la base de datos.
    3. Envuelve toda la ejecución en un bloque `try...except`.
    4. **Por cada paso lógico:**
        a. Actualiza el `JSONField` `steps` para marcar el paso actual como `in_progress` y guarda la hora de inicio.
        b. Ejecuta la acción (ej: llamar a una API externa, crear un documento).
        c. Si tiene éxito, actualiza el paso a `completed` y guarda la hora de finalización.
    5. Si todos los pasos se completan, actualiza el estado general del `WorkflowExecution` a `completed`.
    6. **Si ocurre una excepción:**
        a. Actualiza el estado general a `failed`.
        b. Actualiza el estado del paso actual a `failed`.
        c. Guarda el mensaje de la excepción en el campo `error_detail` del `WorkflowExecution`.

### 3.4. Nuevo Endpoint de Consulta (`apps.workflows.views.WorkflowExecutionStatusView`)

- **URL:** `GET /api/workflows/executions/<execution_id>/`
- **Responsabilidad:** Proveer el estado actualizado de una ejecución.
- **Lógica:**
    1. Recibe el `id` de la ejecución como parámetro en la URL.
    2. Busca el objeto `WorkflowExecution` correspondiente.
    3. Serializa el objeto y lo devuelve como respuesta JSON, incluyendo el estado general, los detalles del error (si existen) y la estructura completa de `steps`.
