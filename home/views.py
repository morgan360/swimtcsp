from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from django.http import Http404
from home.forms import ContactForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from utils.terms_utils import get_current_term


def info_view(request, section=None):
    section = section.lower() if section else 'both'

    # Contact form logic
    form = ContactForm(request.POST or None)
    success = False
    if request.method == 'POST' and form.is_valid():
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']

        html_message = render_to_string(
            'emails/contact_confirmation.html',
            {'name': name, 'email': email, 'subject': subject, 'message': message}
        )

        send_mail(
            f"Contact Us - {subject}",
            '',
            settings.FROM_EMAIL,
            [email],
            html_message=html_message,
        )
        success = True

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
