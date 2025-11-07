from django.urls import path
from .views import ErpNextPosInvoiceWebhookView

urlpatterns = [
    path('webhooks/erpnext/pos-invoice/', ErpNextPosInvoiceWebhookView.as_view(), name='erpnext-pos-invoice-webhook'),
]
