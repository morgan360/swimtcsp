from django.shortcuts import render


def custom_handler404(request, exception, template_name="404.html"):
    return render(request, template_name, status=404)


def custom_handler500(request, template_name="500.html"):
    return render(request, template_name, status=500)


def custom_handler403(request, exception, template_name="403.html"):
    return render(request, template_name, status=403)


def custom_handler401(request, template_name="401.html"):
    return render(request, template_name, status=401)


def custom_handler503(request, template_name="503.html"):
    return render(request, template_name, status=503)


def csrf_failure_view(request, reason="", template_name="403.html"):
    """Render a friendly page for CSRF failures (403)."""
    return render(request, template_name, status=403)
