from django.http import HttpResponseForbidden

from . import services


class AttackBlockMiddleware:
    """Turn away addresses under a block, and count what scanners ask for. First
    in the chain, so a blocked address costs no session or view."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if services.ip_is_blocked(request):
            return HttpResponseForbidden("Blocked. Try again later.", content_type="text/plain")
        response = self.get_response(request)
        services.note_response(request, response.status_code)
        return response
