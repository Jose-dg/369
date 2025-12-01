from django.urls import path
from .views import ErpNextPosInvoiceWebhookView, ShopifyOrderWebhookView, ManualOrderCreateProxyView

urlpatterns = [
    path('webhooks/erpnext/pos-invoice/', ErpNextPosInvoiceWebhookView.as_view(), name='erpnext-pos-invoice-webhook'),
    path('webhooks/shopify/order-create/', ShopifyOrderWebhookView.as_view(), name='shopify-webhook-order-create'),
    path('manual/order/create/', ManualOrderCreateProxyView.as_view(), name='manual-order-create'),
]

