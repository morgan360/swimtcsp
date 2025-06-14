from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from home.forms import ContactForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import user_passes_test
from utils.user_in_group import user_in_group
from django.contrib.auth.decorators import login_required
from utils.terms_utils import get_current_term


def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Render the HTML template for the email
            html_message = render_to_string(
                'emails/contact_confirmation.html', {'name': name, 'email':
                    email, 'subject': subject, 'message': message})

            # Send email to recipient
            send_mail(
                f"Contact Us - {subject}",
                '',  # Use an empty string for the plain text content
                settings.FROM_EMAIL,  # From email address (your email)
                [email],
                # To email addresses (recipient's email)
                html_message=html_message,
            )

            # Send confirmation email to the person who filled out the form
            # send_mail(
            #     f"Thank you for contacting us",
            #     '',  # Use an empty string for the plain text content
            #     settings.FROM_EMAIL,  # From email address (your email)
            #     [settings.FROM_EMAIL],  # To email addresses (user's email)
            #     html_message=html_message,
            # )

            return render(request, 'contact_success.html')
    else:
        form = ContactForm()
    return render(request, 'contact_form.html', {'form': form})


def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

@login_required()
def management(request):
    return render(request, 'management.html')


# Test page
def test_daisyui(request):
    return render(request, 'test_daisyui.html')