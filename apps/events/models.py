import uuid, hashlib, json
from django.db import models
from django_multitenant.mixins import TenantModelMixin

class Event(TenantModelMixin, models.Model):
    STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('dead', 'Dead-letter'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, db_index=True)
    source = models.CharField(max_length=50)
    topic = models.CharField(max_length=255, db_index=True)
    payload = models.JSONField()
    idempotency_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    dedup_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(null=True, blank=True)
    response = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending', db_index=True)
    trace_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    tenant_id = 'organization_id'

    class Meta:
        indexes = [
            models.Index(fields=['organization', 'topic', 'status']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'idempotency_key'],
                                    name='uniq_org_idempotency_key')
        ]
