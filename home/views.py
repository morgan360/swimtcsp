from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from users.utils.roles import is_guardian
from home.forms import ContactForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from utils.terms_utils import get_current_term

def getting_started(request):
    return render(request, "getting_started.html")


def info_view(request, section=None):
    section = section.lower() if section else 'both'

    # Contact form logic
    form = ContactForm(request.POST or None)
    success = False
    if request.method == 'POST' and form.is_valid():
        # Honeypot check: if the hidden field was filled, silently pretend success
        # (bots think they succeeded, no email is sent)
        if form.cleaned_data.get('website'):
            success = True
        else:
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            html_message = render_to_string(
                'emails/contact_confirmation.html',
                {'name': name, 'email': email, 'subject': subject, 'message': message}
            )

            from django.core.mail import EmailMessage

            # Reply-To is the person who wrote in, so hitting Reply in the
            # support inbox answers them. It used to be swimming@ itself, which
            # meant replying to an enquiry sent it straight back to ourselves.
            # Safe to take from the form: ContactForm.email is an EmailField, and
            # Django rejects newlines in headers regardless.
            email_msg = EmailMessage(
                subject=f"Contact Us - {subject}",
                body='',
                from_email=settings.FROM_EMAIL,
                to=[settings.DEFAULT_SUPPORT_EMAIL],
                reply_to=[email],
            )
            email_msg.content_subtype = 'html'
            email_msg.body = html_message
            email_msg.send()
            success = True

    if success:
        form = ContactForm()  # Reset form after successful submission

    if section in ['about', 'contact', 'both']:
        return render(request, 'info.html', {
            'section': section,
            'form': form,
            'success': success
        })

    raise Http404("Invalid section")

def home(request):
    return render(request, 'home.html')


@login_required
def management(request):
    return render(request, 'management.html')


def privacy(request):
    return render(request, 'privacy.html')


@require_http_methods(["GET"])
def check_guardian_access(request):
    """
    API endpoint to check if user is authenticated and in the Guardian group.
    The Guardian role is the single source of truth for dashboard access.
    """
    authenticated = request.user.is_authenticated
    return JsonResponse({
        'is_authenticated': authenticated,
        'is_guardian': is_guardian(request.user, include_superuser=False) if authenticated else False,
    })
