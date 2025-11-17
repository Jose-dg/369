from django.urls import path
from apps.workflows.views import WebhookReceiverView, IntercompanyTransferView

urlpatterns = [
    path('webhook', WebhookReceiverView.as_view(), name='webhook_receiver'),
    path('intercompany-transfer', IntercompanyTransferView.as_view(), name='intercompany_transfer'),
]
