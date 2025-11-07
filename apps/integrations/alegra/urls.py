from django.urls import path
from . import views

urlpatterns = [
    path('resend-invoice/', views.ResendInvoiceAPIView.as_view(), name='resend-alegra-invoice'),
]
