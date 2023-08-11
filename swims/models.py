from django.db import models
from django.db.models.signals import pre_save
from django.utils.text import slugify
from django.urls import reverse
from datetime import date


# Swim masters, aquafit etc
class PublicSwimCategory(models.Model):
    name = models.CharField(max_length=100, null=True)
    slug = models.SlugField(max_length=200,
                            unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'Public Swim Category'
        verbose_name_plural = "Public Swim Categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('swims:product_list_by_category',
                       args=[self.slug])


# List of all the swims
class PublicSwimProduct(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PublicSwimCategory, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, blank=True)
    start_time = models.TimeField(blank=True)
    end_time = models.TimeField(blank=True)
    day_of_week = models.IntegerField(choices=[
        (0, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ], blank=True)
    num_places = models.IntegerField(null=True)
    available = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                              default='images/default_image.jpg')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # if not self.swimprice_set.exists():
        #     PriceVariant.objects.create(product=self, price=10.0)

    class Meta:
        verbose_name = 'Public Swim Times'
        verbose_name_plural = "Public Swim Times"
        ordering = ['day_of_week']

    def get_absolute_url(self):
        return reverse('swims:product_detail',
                       args=[self.id, self.slug])

    def __str__(self):
        start_time_formatted = self.start_time.strftime("%H:%M %p")
        return str(self.category) + " " + str(self.day_of_week) + " " + \
            start_time_formatted


# Prices for OAP, Children etc.
class PriceVariant(models.Model):
    VARIANT_CHOICES = [
        ('Adult', 'Adult'),
        ('Child', 'Child'),
        ('OAP', 'OAP'),
        ('Student', 'Student'),
    ]
    product = models.ForeignKey(PublicSwimProduct, on_delete=models.CASCADE,
                                related_name='price_variants')
    variant = models.CharField(max_length=10, choices=VARIANT_CHOICES,
                               blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, )

    def __str__(self):
        return f'{self.product.name} - {self.variant}'

    def get_price(self):
        return self.price
