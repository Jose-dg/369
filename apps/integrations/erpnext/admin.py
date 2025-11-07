from django.contrib import admin
from .models import ErpnextCredential

@admin.register(ErpnextCredential)
class ErpnextCredentialAdmin(admin.ModelAdmin):
    list_display = ('organization', 'is_active', 'created_at')
    search_fields = ('organization__name',)
    list_filter = ('is_active', 'organization')
    readonly_fields = ('created_at',)