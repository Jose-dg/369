from django.urls import path
from .views import ErpNextPosInvoiceWebhookView, ShopifyOrderWebhookView, OrderCreateProxyView

urlpatterns = [
    path('webhooks/erpnext/pos-invoice/', ErpNextPosInvoiceWebhookView.as_view(), name='erpnext-pos-invoice-webhook'),
    path('webhooks/shopify/order-create/', ShopifyOrderWebhookView.as_view(), name='shopify-webhook-order-create'),
    path('webhook/order/create/', OrderCreateProxyView.as_view(), name='order-create'),
]

