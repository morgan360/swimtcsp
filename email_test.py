from decouple import config
import os
import django
from django.core.mail import EmailMessage, get_connection

# Load settings module from .env
settings_module = config('DJANGO_SETTINGS_MODULE')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

django.setup()

conn = get_connection(fail_silently=False)

# Choose message based on environment
if settings_module == 'config.production_settings':
    body = '✅ This email was sent from the **PRODUCTION** environment.'
else:
    body = '🛠 This email was sent from the **LOCAL/DEV** environment.'

email = EmailMessage(
    subject='TCSP Email Environment Test',
    body=body,
    from_email='web@tcsp.ie',
    to=['morganmcknight@gmail.com'],
    connection=conn,
)

try:
    email.send()
    print("✅ Email sent successfully!")
except Exception as e:
    print("❌ Email failed to send:")
    print(e)
