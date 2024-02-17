from django.db import models
from django.urls import reverse
from datetime import time
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

# School Information
class ScoSchool(models.Model):
    sco_name = models.CharField(max_length=50, default='', blank=True)
    roll_num = models.CharField(max_length=7, default='', blank=True)
    add1 = models.CharField(max_length=50, default='', blank=True)
    add2 = models.CharField(max_length=50, default='', blank=True)
    add3 = models.CharField(max_length=50, default='', blank=True)
    eircode = models.CharField(max_length=7, default='', blank=True)
    phone = models.CharField(max_length=50, default='', blank=True)
    email = models.EmailField(max_length=50, default='', blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__ (self):
        return self.sco_name



# Different schools
class ScoArea(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


# A Program is a collection of Lessons
class ScoProgram(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


# A list of categores of lessons
class ScoCategory(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200,
                            unique=True, blank=True)
    program = models.ForeignKey(ScoProgram, on_delete=models.CASCADE, related_name="sco_categories")

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'School category'
        verbose_name_plural = 'School categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('schools:schools_list_by_category',
                       args=[self.slug])


#     Lessons
class ScoLessons(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(ScoCategory, on_delete=models.CASCADE)
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
    school = models.ForeignKey(
        ScoSchool,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='school_lessons'  # Optional: sets a name for the reverse relation from ScoSchool to ScoTerm
    )

    def save(self, *args, **kwargs):
        # Create the name by combining other fields
        self.name = self.generate_name()
        super().save(*args, **kwargs)

    def generate_name(self):
        return f"{self.category} - " \
               f"{dict(self.DAY_CHOICES).get(self.day_of_week)} - {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')}"

    class Meta:
        verbose_name = 'School Lessons'
        verbose_name_plural = "School Lessons"
        ordering = ['day_of_week']

    def get_absolute_url(self):
        return reverse('schools:detail',
                       args=[self.id, self.slug])

    def __str__(self):
        start_time_formatted = self.start_time.strftime("%H:%M %p")
        day_of_week = dict(self.DAY_CHOICES).get(self.day_of_week)
        return f"{self.category} {day_of_week} {start_time_formatted}"

    def get_num_sold(self):
        from schools_bookings.models import ScoEnrollment
        return ScoEnrollment.objects.filter(lesson=self).count()  # Count the number of related orders

    def get_num_left(self):
        return self.num_places - self.get_num_sold()

    # new method
    def remaining_spaces(self):
        enrollments_count = self.scoenrollment_set.count()
        return max(self.num_places - enrollments_count, 0)

    @property
    def is_full(self):
        return self.remaining_spaces() == 0


# update name everytime fields are changed
@receiver(pre_save, sender=ScoLessons)
def update_product_name(sender, instance, **kwargs):
    instance.name = instance.generate_name()
    instance.slug = slugify(instance.name)


# Create Slug
@receiver(pre_save, sender=ScoCategory)
def update_category_slug(sender, instance, **kwargs):
    if not instance.slug:  # Generate slug only if it doesn't already exist
        instance.slug = slugify(instance.name)

        # Ensure slug uniqueness (basic example)
        original_slug = instance.slug
        queryset = ScoCategory.objects.filter(slug__iexact=instance.slug)
        if instance.pk:  # Exclude current instance in case of update
            queryset = queryset.exclude(pk=instance.pk)
        count = 1
        while queryset.exists():
            instance.slug = f"{original_slug}-{count}"
            count += 1
            queryset = ScoCategory.objects.filter(slug__iexact=instance.slug)
            if instance.pk:
                queryset = queryset.exclude(pk=instance.pk)


