from django.contrib import admin
from .models import AlegraCredential, AlegraInvoice

@admin.register(AlegraCredential)
class AlegraCredentialAdmin(admin.ModelAdmin):
    list_display = ('company', 'api_key', 'api_secret', 'is_active', 'created_at')
    search_fields = ('company__name',)
    list_filter = ('is_active', 'company')
    readonly_fields = ('created_at',)

@admin.register(AlegraInvoice)
class AlegraInvoiceAdmin(admin.ModelAdmin):
    list_display = ('company', 'status', 'alegra_id', 'created_at')
    search_fields = ('company__name', 'alegra_id')
    list_filter = ('status', 'company')
    readonly_fields = ('id', 'created_at', 'updated_at', 'payload_sent', 'response_received')