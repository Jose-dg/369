from django.urls import path
from . import views

app_name = 'erpnext'

urlpatterns = [
    path('pos-invoice-kpis/', views.PosInvoiceKpiView.as_view(), name='pos-invoice-kpis'),
]
