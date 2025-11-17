# core/middleware/tenant.py
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest
from django_multitenant.utils import set_current_tenant
from apps.organizations.models import Organization  # ajusta al nombre real de tu modelo

def _extract_tenant_slug(request: HttpRequest) -> str | None:
    # 1) Por header (útil para APIs / gateways)
    slug = request.headers.get("X-Organization-Slug") or request.headers.get("X-Tenant")
    if slug:
        return slug.strip().lower()

    # 2) Por subdominio (p.ej. acme.julizen.com)
    host = request.get_host().split(":")[0]
    parts = host.split(".")
    # si tu dominio raíz es julizen.com, el subdominio sería parts[0]
    if len(parts) >= 3:
        return parts[0].lower()

    return None

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        slug = _extract_tenant_slug(request)
        print(f"--- [DEBUG] TenantMiddleware: Extracted slug: {slug} ---")
        tenant = None
        if slug:
            try:
                tenant = Organization.objects.get(slug=slug, is_active=True)
                print(f"--- [DEBUG] TenantMiddleware: Found tenant: {tenant.slug} ---")
            except Organization.DoesNotExist:
                print(f"--- [DEBUG] TenantMiddleware: Tenant with slug '{slug}' not found. ---")
                tenant = None

        # Fija el tenant actual para django-multitenant (thread-local)
        set_current_tenant(tenant)
        # opcional: expón en request
        request.organization = tenant
