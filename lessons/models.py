from django.db import models
from django.urls import reverse
from datetime import time
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify


# The modules here represent the structer of lessons and classes in TCSP.
# Product : represents a series of lessons for a term. Each individual lesson is called a class.
# Lessons: (same as Product) are subsets of Categories which really define a level of courses.
# Categories: are course levels Beginners 1, Beginners 2 etc.
# Program: Then at the highest level  is a group of  categories types, Beginners to advanced.
# Groups: are basically different customer groups: Public Classes, Bisghop Galvin Zion NS, Test School

class Area(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


# A Program is a collection of Lessons
class Program(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

# A list of categores of lessons
class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200,
                            unique=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="categories")

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


#     Lessons
class Product(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, blank=True)
    start_time = models.TimeField(blank=True, default=time(hour=8, minute=0))
    end_time = models.TimeField(blank=True, default=time(hour=9, minute=0))

    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    num_places = models.IntegerField(null=True)
    num_weeks = models.IntegerField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, )
    active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                              default='images/default_image.jpg')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, default=1)

    def save(self, *args, **kwargs):
        # Create the name by combining other fields
        self.name = self.generate_name()
        super().save(*args, **kwargs)

    def generate_name(self):
        return f"{self.category} - " \
               f"{dict(self.DAY_CHOICES).get(self.day_of_week)} - {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')}"

    class Meta:
        verbose_name = 'Lessons'
        verbose_name_plural = "Lessons"
        ordering = ['day_of_week']

    def get_absolute_url(self):
        return reverse('lessons:product_detail',
                       args=[self.id, self.slug])

    def __str__(self):
        start_time_formatted = self.start_time.strftime("%H:%M %p")
        day_of_week = dict(self.DAY_CHOICES).get(self.day_of_week)
        return f"{self.category} {day_of_week} {start_time_formatted}"


# update name everytime fields are changed
@receiver(pre_save, sender=Product)
def update_product_name(sender, instance, **kwargs):
    instance.name = instance.generate_name()
    instance.slug = slugify(instance.name)


@receiver(pre_save, sender=Category)
def update_product_name(sender, instance, **kwargs):
    instance.slug = slugify(instance.name)
