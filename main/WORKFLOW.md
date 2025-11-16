Aquí tienes el plan de acción técnico detallado, dividido por archivos y responsabilidades, para que el equipo de backend pueda ejecutarlo.

Este plan asume que el proyecto Django se llama core y la nueva app se llama workflow.

🏗️ Tarea 1: Configuración del Entorno y la App
Objetivo: Preparar el proyecto para el desarrollo asíncrono y la nueva lógica.

Archivo: requirements.txt

Añadir las nuevas dependencias:

celery
redis
Ejecutar pip install -r requirements.txt.

Línea de Comandos:

Crear la nueva app: python manage.py startapp workflow

Archivo: core/settings.py

Registrar la nueva app en INSTALLED_APPS:

Python

INSTALLED_APPS = [
    ...
    'rest_framework',
    'workflow',
]
Configurar Celery y Redis (usar variables de entorno en producción):

Python

# --- Configuración de Celery ---
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
Archivo: core/celery.py (Nuevo Archivo)

Crear el archivo de instancia de Celery:

Python

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
Archivo: core/__init__.py

Asegurar que Celery se cargue con Django:

Python

from .celery import app as celery_app

__all__ = ('celery_app',)
🗃️ Tarea 2: Definición de Modelos (Base de Datos)
Objetivo: Crear las tablas para almacenar las credenciales de ERPNext y el estado de cada ejecución.

Archivo: workflow/models.py

Implementar los dos modelos clave:

Python

from django.db import models

class ERPNextInstance(models.Model):
    """ Almacena las credenciales para una instancia de ERPNext """
    name = models.CharField(max_length=100, unique=True)
    api_url = models.URLField(help_text="Ej: https://erp.compañia.com")
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class WorkflowExecution(models.Model):
    """ Bitácora y estado de cada flujo de trabajo iniciado """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('step1_po_a', 'Paso 1: PO en A Creado'),
        ('step2_pr_a', 'Paso 2: PR en A Creado'),
        ('step3_dn_a', 'Paso 3: DN en A Creado'),
        ('completed', 'Completado (PR en B Creado)'),
        ('failed', 'Fallido'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Guarda el JSON exacto recibido en la API
    payload_json = models.JSONField(help_text="Payload original de la API")

    # --- Trazabilidad de Documentos Creados ---
    po_a_id = models.CharField(max_length=255, null=True, blank=True)
    pr_a_id = models.CharField(max_length=255, null=True, blank=True)
    dn_a_id = models.CharField(max_length=255, null=True, blank=True)
    pr_b_id = models.CharField(max_length=255, null=True, blank=True)

    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ejecución {self.id} - {self.status}"
Línea de Comandos:

Crear y aplicar las migraciones:

Bash

python manage.py makemigrations workflow
python manage.py migrate
Archivo: workflow/admin.py

Registrar los modelos en el Admin de Django para fácil depuración:

Python

from django.contrib import admin
from .models import ERPNextInstance, WorkflowExecution

@admin.register(ERPNextInstance)
class ERPNextInstanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_url')

@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at', 'po_a_id', 'pr_a_id')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at', 'payload_json')
🔧 Tarea 3: Implementar el Cliente de API (Services)
Objetivo: Crear una clase reutilizable que maneje toda la comunicación HTTP con ERPNext.

Archivo: workflow/services.py (Nuevo Archivo)

Implementar el cliente y las funciones "helper" para construir los JSON.

Python

import requests
from .models import ERPNextInstance

class ERPNextClient:
    def __init__(self, base_url, api_key, api_secret):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret

    def _get_headers(self):
        return {
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        }

    def _post(self, endpoint, data):
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        try:
            response = requests.post(url, json=data, headers=headers, timeout=15)
            response.raise_for_status() # Lanza error en 4xx o 5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            # Idealmente, loguear el error aquí
            raise Exception(f"Error en API {url}: {e}")

    @classmethod
    def from_instance_id(cls, instance_id):
        instance = ERPNextInstance.objects.get(id=instance_id)
        return cls(instance.api_url, instance.api_key, instance.api_secret)

    def create_document(self, doctype, data):
        """ Crea un documento (siempre en borrador, docstatus=0) """
        data['docstatus'] = 0 
        response = self._post(f'/api/resource/{doctype}', data)
        return response.get('data')

    def submit_document(self, doctype, docname):
        """ Hace 'Submit' a un documento ya creado """
        return self._post('/api/method/frappe.client.submit', {
            "doctype": doctype,
            "docname": docname
        })

# --- FUNCIONES HELPER (LÓGICA DE NEGOCIO) ---

def build_po_data(payload):
    # Lógica para construir el JSON del Purchase Order
    # ...
    return {
        "supplier": payload['supplier'],
        "company": payload['company_a_name'], # Asumir que esto viene en el payload
        "items": [
            {
                "item_code": item['item_code'],
                "qty": item['qty'],
                "rate": item['rate'],
                "warehouse": payload['company_a_warehouse']
            } for item in payload['items']
        ]
    }

def build_pr_data(payload, po_name):
    # Lógica para construir el JSON del Purchase Receipt
    items_data = []
    for item in payload['items']:
        # Formato CRÍTICO de seriales: string separado por \n
        serials_str = "\n".join(item['serials'])
        items_data.append({
            "item_code": item['item_code'],
            "qty": item['qty'],
            "rate": item['rate'],
            "warehouse": payload['company_a_warehouse'],
            "purchase_order": po_name, # Vínculo con el PO
            "serial_no": serials_str
        })
    return {"items": items_data}

def build_dn_data(payload):
    # Lógica para construir el JSON del Delivery Note
    items_data = []
    for item in payload['items']:
        serials_str = "\n".join(item['serials'])
        items_data.append({
            "item_code": item['item_code'],
            "qty": item['qty'],
            "warehouse": payload['company_a_warehouse'],
            "serial_no": serials_str
        })
    return {
        "customer": payload['company_b_customer_name'], # DATO CRÍTICO
        "items": items_data
    }

def build_pr_b_data(payload):
    # Lógica para construir el PR en la Compañía B
    items_data = []
    for item in payload['items']:
        serials_str = "\n".join(item['serials'])
        items_data.append({
            "item_code": item['item_code'],
            "qty": item['qty'],
            "warehouse": payload['company_b_warehouse'],
            "serial_no": serials_str
        })
    return {
        "supplier": payload['company_a_supplier_name'], # DATO CRÍTICO
        "items": items_data
    }
⚙️ Tarea 4: Crear la Tarea Asíncrona (Celery)
Objetivo: Implementar la lógica de orquestación de 4 pasos de forma robusta y reanudable.

Archivo: workflow/tasks.py (Nuevo Archivo)

Python

from celery import shared_task
from .models import WorkflowExecution
from .services import (
    ERPNextClient, build_po_data, build_pr_data, 
    build_dn_data, build_pr_b_data
)
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, max_retries=5)
def run_full_transfer_workflow(self, execution_id):
    try:
        exec = WorkflowExecution.objects.get(id=execution_id)
        if exec.status == 'completed':
            logger.warning(f"[{exec.id}] Flujo ya completado.")
            return "Ya completado."

        payload = exec.payload_json

        # Clientes de API
        client_a = ERPNextClient.from_instance_id(payload['company_a_instance_id'])
        client_b = ERPNextClient.from_instance_id(payload['company_b_instance_id'])

        # --- Paso 1: Crear PO en A ---
        if not exec.po_a_id:
            logger.info(f"[{exec.id}] Paso 1: Creando PO en A...")
            po_data = build_po_data(payload)
            po_doc = client_a.create_document('Purchase Order', po_data)
            client_a.submit_document('Purchase Order', po_doc['name'])

            exec.po_a_id = po_doc['name']
            exec.status = 'step1_po_a'
            exec.save()

        # --- Paso 2: Crear PR en A ---
        if not exec.pr_a_id:
            logger.info(f"[{exec.id}] Paso 2: Creando PR en A...")
            pr_data = build_pr_data(payload, po_name=exec.po_a_id)
            pr_doc = client_a.create_document('Purchase Receipt', pr_data)
            client_a.submit_document('Purchase Receipt', pr_doc['name'])

            exec.pr_a_id = pr_doc['name']
            exec.status = 'step2_pr_a'
            exec.save()

        # --- Paso 3: Crear DN en A ---
        if not exec.dn_a_id:
            logger.info(f"[{exec.id}] Paso 3: Creando DN en A...")
            dn_data = build_dn_data(payload)
            dn_doc = client_a.create_document('Delivery Note', dn_data)
            client_a.submit_document('Delivery Note', dn_doc['name'])

            exec.dn_a_id = dn_doc['name']
            exec.status = 'step3_dn_a'
            exec.save()

        # --- Paso 4: Crear PR en B ---
        if not exec.pr_b_id:
            logger.info(f"[{exec.id}] Paso 4: Creando PR en B...")
            pr_b_data = build_pr_b_data(payload)
            pr_b_doc = client_b.create_document('Purchase Receipt', pr_b_data)
            client_b.submit_document('Purchase Receipt', pr_b_doc['name'])

            exec.pr_b_id = pr_b_doc['name']
            exec.status = 'completed'
            exec.save()

        logger.info(f"[{exec.id}] Flujo completado exitosamente.")
        return f"Éxito: {exec.id}"

    except Exception as e:
        logger.error(f"[{execution_id}] Fallo en el flujo: {e}", exc_info=True)
        if 'exec' in locals():
            exec.status = 'failed'
            exec.error_message = str(e)
            exec.save()
        raise self.retry(exc=e) # Reintentar
🔌 Tarea 5: Crear el Endpoint (API)
Objetivo: Exponer la API que recibe la solicitud, la valida y lanza la tarea asíncrona.

Archivo: workflow/serializers.py (Nuevo Archivo)

Crear un serializer para validar el payload de entrada.

Python

from rest_framework import serializers

class ItemSerializer(serializers.Serializer):
    item_code = serializers.CharField(max_length=100)
    qty = serializers.IntegerField(min_value=1)
    rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    serials = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

class FullWorkflowSerializer(serializers.Serializer):
    # IDs de las instancias de ERPNext (PK del modelo ERPNextInstance)
    company_a_instance_id = serializers.IntegerField()
    company_b_instance_id = serializers.IntegerField()

    # Nombres de entidades en ERPNext
    supplier = serializers.CharField(max_length=100)
    company_a_name = serializers.CharField(max_length=100)
    company_b_customer_name = serializers.CharField(max_length=100)
    company_a_supplier_name = serializers.CharField(max_length=100)

    # Almacenes
    company_a_warehouse = serializers.CharField(max_length=100)
    company_b_warehouse = serializers.CharField(max_length=100)

    # Items
    items = ItemSerializer(many=True, allow_empty=False)
Archivo: workflow/views.py

Implementar la vista de API.

Python

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated # ¡Asegurar esto!
from .models import WorkflowExecution
from .tasks import run_full_transfer_workflow
from .serializers import FullWorkflowSerializer

class StartFullWorkflowView(APIView):
    """
    Inicia el flujo de 4 pasos para registrar una compra de PINES
    y transferirlos entre compañías.
    """
    permission_classes = [IsAuthenticated] # Usar auth de DRF

    def post(self, request, *args, **kwargs):
        serializer = FullWorkflowSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payload = serializer.validated_data

        try:
            # Crear el registro de ejecución
            execution = WorkflowExecution.objects.create(
                status='pending',
                payload_json=payload 
            )

            # Lanzar la tarea asíncrona
            run_full_transfer_workflow.delay(execution_id=execution.id)

            # Responder INMEDIATAMENTE
            return Response(
                {"message": "Flujo de trabajo aceptado", "execution_id": execution.id},
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"error": f"Error al iniciar el flujo: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
Archivo: workflow/urls.py (Nuevo Archivo)

Definir la URL para la vista.

Python

from django.urls import path
from .views import StartFullWorkflowView

urlpatterns = [
    path('start-workflow/', StartFullWorkflowView.as_view(), name='start_workflow'),
]
Archivo: core/urls.py

Incluir las URLs de la app workflow.

Python

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/workflow/', include('workflow.urls')),
    # ... otras urls
]
🚀 Tarea 6: Probar
Asegurarse de que Redis esté corriendo: redis-server

Iniciar el worker de Celery: celery -A core worker -l info

Iniciar el servidor de Django: python manage.py runserver

Poblar el Admin de Django con las instancias de ERPNextInstance.

Enviar una petición POST al endpoint /api/v1/workflow/start-workflow/ con el payload JSON completo y un token de autenticación válido.

Monitorear la consola del worker de Celery y el Admin de Django (WorkflowExecution) para ver el progreso del flujo.



API Key
457d72662d1184a

API Secret
9a1b959b1ee639d

