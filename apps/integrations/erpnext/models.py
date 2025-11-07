import uuid
from django.db import models
from django_multitenant.mixins import TenantModelMixin

class ErpnextCredential(TenantModelMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='erpnext_credentials')
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    erpnext_site_url = models.URLField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    tenant_id = 'organization_id'