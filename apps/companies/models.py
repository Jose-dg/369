from django.db import models
import uuid
from apps.organizations.models import Organization

class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=255)
    alegra_id = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'name')
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['-created_at']