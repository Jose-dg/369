import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_multitenant.mixins import TenantModelMixin

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class Membership(TenantModelMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=50, default='member')
    is_active = models.BooleanField(default=True)

    tenant_id = 'organization_id'

    class Meta:
        unique_together = ('user', 'organization')

