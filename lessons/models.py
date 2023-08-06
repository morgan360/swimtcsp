from django.db import models
from django.urls import reverse
from datetime import time
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Category(models.Model):
    LEVEL_CHOICES = [
        ('Beginners', 'Beginners'),
        ('Improvers', 'Improvers'),
        ('Advanced', 'Advanced'),
        ('Lengths', 'Lengths'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200,
                            unique=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('lessons:product_list_by_category',
                       args=[self.slug])


class Product(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, blank=True)
    start_time = models.TimeField(blank=True, default=time(hour=8, minute=0))
    end_time = models.TimeField(blank=True, default=time(hour=9, minute=0))
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES,
                                   blank=True)
    num_places = models.IntegerField(null=True)
    num_weeks = models.IntegerField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, )
    available = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                              default='images/default_image.jpg')

    def save(self, *args, **kwargs):
        # Create the name by combining other fields
        self.name = self.generate_name()
        super().save(*args, **kwargs)

    def generate_name(self):
        return f"{self.category} - {self.day_of_week} - {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')}"

    class Meta:
        verbose_name = 'Lessons'
        verbose_name_plural = "Lessons"
        ordering = ['day_of_week']

    def get_absolute_url(self):
        return reverse('lessons:product_detail',
                       args=[self.id, self.slug])

    def __str__(self):
        start_time_formatted = self.start_time.strftime("%H:%M %p")
        return str(
            self.category) + " " + self.day_of_week + " " + start_time_formatted


# update name everytime fields are changed
@receiver(pre_save, sender=Product)
def update_product_name(sender, instance, **kwargs):
    instance.name = instance.generate_name()
