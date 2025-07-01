from django.core.mail import send_mail
from django.conf import settings

def send_waiting_list_notification(user_email, swimling_name, product_name):
    subject = '🏊 Lesson Slot Now Available for Your Swimling'

    plain_message = (
        f"Dear Parent,\n\n"
        f"A slot is now available for {swimling_name} in the lesson {product_name}.\n"
        f"Please log in to book the slot within the next 7 days.\n\n"
        f"Best regards,\nTCSP Swim Team"
    )

    html_message = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Great News! 🏊</h2>
        <p>A lesson slot is now available for:</p>
        <ul>
          <li><strong>Swimling:</strong> {swimling_name}</li>
          <li><strong>Lesson:</strong> {product_name}</li>
        </ul>
        <p>Please log in to your account and book the slot within the next <strong>7 days</strong>.</p>
        <p>If you have any questions, feel free to reply to this email.</p>
        <br>
        <p>See you at the pool!<br>— TCSP Swim Team</p>
      </body>
    </html>
    """

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
        html_message=html_message
    )

