# Different Footor for each version
def footer_message(request):
    from django.conf import settings
    return {'FOOTER_MESSAGE': settings.FOOTER_MESSAGE}