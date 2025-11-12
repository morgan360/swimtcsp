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
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Full term price (auto-calculated as weekly_price × num_weeks). Leave blank - will be set automatically.'
    )
    weekly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Price per lesson (weekly). Full term price is calculated as weekly_price × num_weeks.'
    )
    active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                              default='images/default_image.jpg')

    def save(self, *args, **kwargs):
        # Auto-calculate full term price from weekly_price
        if self.weekly_price and self.num_weeks:
            from decimal import Decimal
            self.price = (self.weekly_price * Decimal(str(self.num_weeks))).quantize(Decimal('0.01'))

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

    def get_full_term_price(self):
        """
        Calculate the full term price from weekly_price × num_weeks.
        Falls back to legacy 'price' field if weekly_price is not set.

        Returns:
            Decimal: Full term price
        """
        from decimal import Decimal

        if self.weekly_price and self.num_weeks:
            return (self.weekly_price * Decimal(str(self.num_weeks))).quantize(Decimal('0.01'))

        # Fallback to legacy price field
        return self.price or Decimal('0.00')

    def count_lessons_remaining(self, term, from_date=None):
        """
        Count how many lessons remain from the next occurrence of this class day
        until the end of the term.

        Args:
            term: Term object
            from_date: Date to count from (defaults to today)

        Returns:
            int: Number of lessons remaining
        """
        from django.utils import timezone

        if not term:
            return 0

        if from_date is None:
            from_date = timezone.now().date()

        # If term hasn't started yet, return total weeks
        if from_date < term.start_date:
            return self.num_weeks or 0

        # If term has ended, return 0
        if from_date > term.end_date:
            return 0

        # Find the next occurrence of this class day
        days_until_class_day = (self.day_of_week - from_date.weekday()) % 7
        if days_until_class_day == 0:
            # Today is the class day - check if we should include today or start from next week
            # Include today's class
            next_class_date = from_date
        else:
            next_class_date = from_date + timedelta(days=days_until_class_day)

        # Count occurrences of this day from next_class_date to term end
        lessons_count = 0
        current_date = next_class_date

        while current_date <= term.end_date:
            lessons_count += 1
            current_date += timedelta(days=7)  # Move to next week

        return lessons_count

    def get_prorated_price(self, term):
        """
        Calculate the prorated price based on lessons remaining in the term.

        Args:
            term: Term object to calculate pricing for

        Returns:
            Decimal: Prorated price based on lessons remaining

        Logic:
            - If term hasn't started yet: return full term price
            - If term has started: count lessons remaining from next class date
            - Return weekly_price × lessons_remaining
            - Minimum charge is always 1 lesson
        """
        from decimal import Decimal
        from django.utils import timezone

        if not term:
            return self.get_full_term_price()

        # Use weekly_price if available, otherwise fall back to calculating from price
        if self.weekly_price:
            price_per_lesson = self.weekly_price
        elif self.price and self.num_weeks:
            # Legacy: calculate from full price
            price_per_lesson = self.price / Decimal(str(self.num_weeks))
        else:
            return Decimal('0.00')

        today = timezone.now().date()

        # If term hasn't started yet, charge full term price
        if today < term.start_date:
            return self.get_full_term_price()

        # If term has ended, return 0
        if today > term.end_date:
            return Decimal('0.00')

        # Count lessons remaining from next occurrence of this class day
        lessons_remaining = self.count_lessons_remaining(term, from_date=today)

        # Ensure minimum of 1 lesson
        if lessons_remaining < 1:
            lessons_remaining = 1

        # Calculate prorated price
        prorated_price = price_per_lesson * Decimal(str(lessons_remaining))

        return prorated_price.quantize(Decimal('0.01'))


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
