from django.db import models

from django.db import models
from django.conf import settings

class WorkflowExecution(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='workflows'
    )
    pr_id_a = models.CharField(max_length=255, help_text="ID of Purchase Receipt from Company A")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    dn_id_a = models.CharField(max_length=255, null=True, blank=True, help_text="ID of Delivery Note in Company A")
    pr_id_b = models.CharField(max_length=255, null=True, blank=True, help_text="ID of Purchase Receipt in Company B")
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workflow {self.id} - PR A: {self.pr_id_a} - Status: {self.status}"