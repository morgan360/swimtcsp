from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from lessons.models import Product
from users.models import Swimling


class WaitingList(models.Model):
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_transfer_request = models.BooleanField(default=False)
    has_sibling_booked = models.BooleanField(default=False)

    preferred_lesson_1 = models.ForeignKey(
        Product, related_name='preferred_1', null=True, blank=True, on_delete=models.SET_NULL
    )
    preferred_lesson_2 = models.ForeignKey(
        Product, related_name='preferred_2', null=True, blank=True, on_delete=models.SET_NULL
    )
    preferred_lesson_3 = models.ForeignKey(
        Product, related_name='preferred_3', null=True, blank=True, on_delete=models.SET_NULL
    )

    is_notified = models.BooleanField(default=False)
    notification_date = models.DateTimeField(null=True, blank=True)
    assigned_lesson = models.ForeignKey(
        Product, related_name='assigned_lessons', on_delete=models.SET_NULL, null=True, blank=True
    )
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('swimling', 'product')

    def clean(self):
        if self.swimling and self.product:
            if WaitingList.objects.filter(swimling=self.swimling, product=self.product).exclude(id=self.id).exists():
                raise ValidationError('This swimling is already on the waiting list for this lesson.')

    def check_sibling_bookings(self):
        if not self.swimling or not self.swimling.guardian:
            return
        siblings = Swimling.objects.filter(guardian=self.swimling.guardian).exclude(id=self.swimling.id)
        current_term_bookings = Product.objects.filter(
            enrollments__swimling__in=siblings,
            enrollments__term__start_date__lte=timezone.now().date(),
            enrollments__term__end_date__gte=timezone.now().date()
        ).distinct()
        self.has_sibling_booked = current_term_bookings.exists()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_assigned_lesson = None

        # Check for sibling
        self.check_sibling_bookings()

        if not is_new:
            old = WaitingList.objects.get(pk=self.pk)
            old_assigned_lesson = old.assigned_lesson

        super().save(*args, **kwargs)

        if is_new:
            self.send_joined_waiting_list_email()

        if self.assigned_lesson and self.assigned_lesson != old_assigned_lesson:
            if not self.is_notified:
                self.is_notified = True
                self.notification_date = timezone.now()
                self.send_notification_email()
                super().save(update_fields=["is_notified", "notification_date"])

    def send_notification_email(self):
        guardian = self.swimling.guardian
        if guardian.email and self.assigned_lesson:
            subject = "Lesson Available for Your Swimling"
            from_email = settings.DEFAULT_FROM_EMAIL
            to = [guardian.email]
            context = {
                'guardian': guardian,
                'swimling': self.swimling,
                'lesson': self.assigned_lesson,
            }
            text_content = render_to_string('emails/waiting_list_notification.txt', context)
            html_content = render_to_string('emails/waiting_list_notification.html', context)
            email = EmailMultiAlternatives(subject, text_content, from_email, to)
            email.attach_alternative(html_content, "text/html")
            email.send()

    def send_joined_waiting_list_email(self):
        guardian = self.swimling.guardian
        if guardian.email:
            subject = "You've Been Added to the Waiting List"
            from_email = settings.DEFAULT_FROM_EMAIL
            to = [guardian.email]
            context = {
                'guardian': guardian,
                'swimling': self.swimling,
                'product': self.product,
            }
            text_content = render_to_string('emails/waiting_list_joined.txt', context)
            html_content = render_to_string('emails/waiting_list_joined.html', context)
            email = EmailMultiAlternatives(subject, text_content, from_email, to)
            email.attach_alternative(html_content, "text/html")
            email.send()

    def __str__(self):
        return f"{self.swimling} - {self.product}"
