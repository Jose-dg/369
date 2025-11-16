from django.urls import path
from .views import ErpNextPosInvoiceWebhookView, ShopifyOrderWebhookView

urlpatterns = [
    path('webhooks/erpnext/pos-invoice/', ErpNextPosInvoiceWebhookView.as_view(), name='erpnext-pos-invoice-webhook'),
    path('webhooks/shopify/order-create/', ShopifyOrderWebhookView.as_view(), name='shopify-webhook-order-create'),
]

