import uuid
from django.db import models
from django_multitenant.mixins import TenantModelMixin
from django_multitenant.fields import TenantForeignKey
from apps.companies.models import Company

class AlegraCredential(TenantModelMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='alegra_credentials')
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    tenant_id = 'company_id'

class AlegraInvoice(TenantModelMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='alegra_invoices')
    event = TenantForeignKey('events.Event', on_delete=models.CASCADE, related_name='alegra_invoice')
    alegra_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=50, db_index=True)
    payload_sent = models.JSONField()
    response_received = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    tenant_id = 'company_id'

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'alegra_id'],
                                    name='uniq_alegra_id_per_company')
        ]