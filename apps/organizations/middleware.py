from django_multitenant.utils import get_current_tenant

class OrganizationContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = get_current_tenant()
        if tenant:
            request.organization = tenant
        response = self.get_response(request)
        return response
