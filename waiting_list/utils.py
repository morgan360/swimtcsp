from django.core.mail import send_mail
from django.conf import settings


def send_waiting_list_notification(user_email, swimling_name, product_name):
    subject = 'Lesson Slot Available'
    message = f'Dear {user_email},\n\nA slot is now available for {swimling_name} in the lesson {product_name}. Please log in to book the slot within the next 7 days.\n\nBest regards,\nYour Swim School'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [user_email]
    send_mail(subject, message, email_from, recipient_list)
