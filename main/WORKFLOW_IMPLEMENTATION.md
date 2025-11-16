# Implementación del Orquestador de Flujo de Trabajo de Inventario

Este documento detalla la implementación de un orquestador para la automatización de flujos de trabajo de inventario en ERPNext, utilizando Django y Celery. El sistema está diseñado para un entorno multi-inquilino (multi-tenant), manejando múltiples organizaciones.

## 1. Resumen de la Arquitectura

-   **Aplicación Django**: Actúa como middleware para orquestar las operaciones.
-   **App Interna**: La lógica se encapsula en una nueva app llamada `workflow`.
-   **Procesamiento Asíncrono**: Se usa `Celery` con `Redis` como broker para manejar las tareas de forma robusta y en segundo plano.
-   **Disparadores**: Endpoints de API que inician los flujos de trabajo.

## 2. Plan de Implementación Detallado

### Paso A: Configuración de Celery y la Nueva App (Completado)

1.  **Dependencias**: Se añadieron `celery` y `redis` al fichero `requirements.txt`.
2.  **Configuración de Celery**: Se configuró Celery en el proyecto Django.
3.  **Creación de la App `workflow`**: Se creó la nueva aplicación y se registró en `INSTALLED_APPS`.

### Paso B: Desarrollo de la App `workflow` (Completado)

1.  **Modelos (`workflow/models.py`)**:
    -   Se utiliza el modelo `ErpnextCredential` existente en la app `apps.integrations.erpnext` para almacenar las credenciales de la API de ERPNext para cada organización.
    -   `WorkflowExecution`: Modelo para registrar cada ejecución del flujo de trabajo de transferencia. Se le añadió una clave foránea al modelo `Organization` para identificar al inquilino.

2.  **Servicios (`workflow/services.py`)**:
    -   `ERPNextClient`: Una clase que maneja la comunicación con la API de ERPNext, utilizando las credenciales del modelo `ErpnextCredential`.

3.  **Tareas Asíncronas (`workflow/tasks.py`)**:
    -   `transfer_inventory_task(workflow_execution_id)`: Tarea de Celery que orquesta la transferencia de inventario entre dos compañías (dos `Organizations` distintas).
    -   `execute_external_purchase_workflow(...)`: Nueva tarea que orquesta el flujo de compra a proveedor externo y la posterior transferencia intercompañía en un solo proceso.

4.  **API Endpoints (`workflow/views.py` y `workflow/urls.py`)**:
    -   `/api/workflow/webhook/`: Endpoint que recibe notificaciones de ERPNext (webhooks) para iniciar el flujo `transfer_inventory_task`. Requiere `organization_id`.
    -   `/api/workflow/external-purchase-workflow/`: Nuevo endpoint que inicia el flujo de compra externa y transferencia. Recibe todos los datos necesarios, incluyendo los números de serie.

### Paso C: Robustez y Alertas (Completado)

1.  **Logging**: Se ha implementado un sistema de logging para registrar información detallada en cada paso de las tareas.
2.  **Alertas**: Se ha omitido la implementación de alertas por correo electrónico por el momento, según lo solicitado.

---

## 3. Flujos de Trabajo Implementados

### Flujo 1: Transferencia de Inventario por Webhook

-   **Disparador**: `POST` a `/api/workflow/webhook/`.
-   **Payload**: `{ "name": "ID_DEL_DOCUMENTO", "organization_id": "ID_DE_LA_ORGANIZACION_A" }`
-   **Proceso**:
    1.  La vista `WebhookReceiverView` recibe la notificación.
    2.  Se crea un registro `WorkflowExecution`.
    3.  Se lanza la tarea `transfer_inventory_task`.
    4.  La tarea lee el `Purchase Receipt` de la Compañía A, crea una `Delivery Note` en la Compañía A y luego un `Purchase Receipt` en la Compañía B (identificada por su nombre).

### Flujo 2: Compra Externa y Transferencia Intercompañía

-   **Disparador**: `POST` a `/api/workflow/external-purchase-workflow/`.
-   **Propósito**: Orquestar el proceso completo desde la compra a un proveedor hasta la recepción en una segunda compañía.
-   **Payload de la Solicitud**:
    ```json
    {
      "supplier": "NombreDelProveedor",
      "organization_id": "ID_Compania_A",
      "warehouse": "Almacen_En_A",
      "items": [{ "item_code": "...", "qty": 100 }],
      "serial_numbers": ["SER001", "SER002", ...],
      "destination_organization_id": "ID_Compania_B",
      "destination_warehouse": "Almacen_En_B"
    }
    ```
-   **Proceso**:
    1.  La vista `ExternalPurchaseWorkflowView` recibe la solicitud.
    2.  Lanza la tarea `execute_external_purchase_workflow` con todos los datos.
    3.  La tarea ejecuta los siguientes pasos de forma secuencial y automática:
        a.  **Crea Recepción de Compra en Compañía A**: Registra la entrada de los productos con sus números de serie.
        b.  **Crea Nota de Entrega desde Compañía A**: Registra la salida de los mismos productos para transferirlos.
        c.  **Crea Recepción de Compra en Compañía B**: Registra la entrada de los productos en el almacén de destino de la segunda compañía.
