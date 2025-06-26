from decouple import config
import os
import django
from django.core.mail import EmailMessage, get_connection

# Load settings module from .env using decouple
os.environ.setdefault('DJANGO_SETTINGS_MODULE', config('DJANGO_SETTINGS_MODULE'))

django.setup()

conn = get_connection(fail_silently=False)

email = EmailMessage(
    subject='Office365 SMTP Standalone Test',
    body='Testing Office365 SMTP using configured settings module.',
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
