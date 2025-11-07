from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'alegra_id', 'created_at')
    search_fields = ('name', 'organization__name')
    list_filter = ('organization',)
    readonly_fields = ('created_at', 'updated_at')