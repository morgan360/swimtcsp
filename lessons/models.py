from django.db import models
from django.urls import reverse
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from datetime import datetime, timedelta, time

# The modules here represent the structer of lessons and classes in TCSP.
# Product : represents a series of lessons for a term. Each individual lesson is called a class.
# Lessons: (same as Product) are subsets of Categories which really define a level of courses.
# Categories: are course levels Beginners 1, Beginners 2 etc.
# Program: Then at the highest level  is a group of  categories types, Beginners to advanced.
# Groups: are basically different customer groups: Public Classes, Bisghop Galvin Zion NS, Test School

# A Program is a collection of Lessons
class Program(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


# A list of categores of lessons
class Category(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    slug = models.SlugField(max_length=200,
                            unique=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="categories")
    STAGE_CHOICES = [
        ("", "---------"),  # blank choice
        ("Stage 1", "Stage 1"),
        ("Stage 2", "Stage 2"),
        ("Stage 3", "Stage 3"),
        ("Stage 4", "Stage 4"),
        ("Stage 5", "Stage 5"),
        ("Stage 6", "Stage 6"),
        ("Stage 7", "Stage 7"),
        ("Stage 8", "Stage 8"),
        ("Stage 9", "Stage 9"),
        ("Stage 10", "Stage 10"),
    ]

    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        blank=True,
        help_text="Optional stage mapping for this category (Stage 1–8)"
    )

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
    # 08:00 and 09:00 are valid Python `datetime.time` objects
    start_time = models.TimeField(
        blank=True,
        null=True,  # let DB accept NULL
        default=time(hour=8, minute=0)
    )
    end_time = models.TimeField(
        blank=True,
        null=True,
        default=time(hour=9, minute=0)
    )

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
        return f"{self.category}: {day_of_week}-{start_time_formatted}"

    def get_num_sold(self, term):
        from lessons_bookings.models import LessonEnrollment
        return LessonEnrollment.objects.filter(lesson=self, term=term).count()

    def get_num_left(self, term):
        return self.num_places - self.get_num_sold(term)

    def remaining_spaces(self, term):
        enrollments_count = self.enrollments.filter(term=term).count()
        return max(self.num_places - enrollments_count, 0)

    def is_full(self, term):
        return self.remaining_spaces(term) == 0

    def get_prorated_price(self, term):
        """
        Calculate the prorated price based on weeks remaining in the term.

        Args:
            term: Term object to calculate pricing for

        Returns:
            Decimal: Prorated price if term has started, full price otherwise

        Logic:
            - If term hasn't started yet: return full price
            - If term has started: return (weeks_remaining / total_weeks) * full_price
            - Minimum charge is always price for 1 week
        """
        from decimal import Decimal
        from django.utils import timezone

        if not term or not self.price or not self.num_weeks:
            return self.price

        today = timezone.now().date()

        # If term hasn't started yet, charge full price
        if today < term.start_date:
            return self.price

        # If term has ended, return 0 (or you could return full price)
        if today > term.end_date:
            return Decimal('0.00')

        # Calculate weeks remaining
        days_remaining = (term.end_date - today).days
        weeks_remaining = (days_remaining / 7)  # Can be fractional

        # Calculate prorated price
        if weeks_remaining <= 0:
            return Decimal('0.00')

        # Calculate price per week
        price_per_week = self.price / Decimal(str(self.num_weeks))
        prorated_price = price_per_week * Decimal(str(weeks_remaining))

        # Ensure minimum of 1 week's price
        min_price = price_per_week

        return max(prorated_price, min_price).quantize(Decimal('0.01'))


# update name everytime fields are changed
@receiver(pre_save, sender=Product)
def update_product_name(sender, instance, **kwargs):
    instance.name = instance.generate_name()
    instance.slug = slugify(instance.name)


# Create Slug
@receiver(pre_save, sender=Category)
def update_category_slug(sender, instance, **kwargs):
    if not instance.slug:  # Generate slug only if it doesn't already exist
        instance.slug = slugify(instance.name)

        # Ensure slug uniqueness (basic example)
        original_slug = instance.slug
        queryset = Category.objects.filter(slug__iexact=instance.slug)
        if instance.pk:  # Exclude current instance in case of update
            queryset = queryset.exclude(pk=instance.pk)
        count = 1
        while queryset.exists():
            instance.slug = f"{original_slug}-{count}"
            count += 1
            queryset = Category.objects.filter(slug__iexact=instance.slug)
            if instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
