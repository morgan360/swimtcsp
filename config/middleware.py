# config/middleware.py

from django.http import HttpResponsePermanentRedirect


class WwwRedirectMiddleware:
    """
    Redirect plain tcsp.ie to www.tcsp.ie (SEO-friendly permanent 301 redirect).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]  # strip port if present
        if host == "tcsp.ie":
            return HttpResponsePermanentRedirect(
                "https://www.tcsp.ie" + request.get_full_path()
            )
        return self.get_response(request)
