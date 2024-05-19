from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from lessons.models import Product
from users.models import Swimling
from django.core.exceptions import ValidationError


class WaitingList(models.Model):
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    notification_date = models.DateTimeField(null=True, blank=True)
    assigned_lesson = models.ForeignKey(Product, related_name='assigned_lessons', on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('swimling', 'product')

    def clean(self):
        if WaitingList.objects.filter(swimling=self.swimling, product=self.product).exclude(id=self.id).exists():
            raise ValidationError('This swimling is already on the waiting list for this lesson.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.swimling} - {self.product}"
