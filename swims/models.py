from django.db import models
from django.db.models.signals import pre_save, post_save
from django.utils.text import slugify
from django.urls import reverse
from datetime import date
from django.dispatch import receiver


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


class PublicSwimProduct(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PublicSwimCategory, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, blank=True)
    start_time = models.TimeField(blank=True)
    end_time = models.TimeField(blank=True)
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
    available = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d', default='images/default_image.jpg')

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.generate_name()

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def generate_name(self):
        return f"{self.category} - {dict(self.DAY_CHOICES).get(self.day_of_week)} - {self.start_time.strftime('%H:%M')}"

    class Meta:
        verbose_name = 'Public Swim'
        verbose_name_plural = "Public Swims"
        ordering = ['day_of_week']

    def get_absolute_url(self):
        return reverse('swims:product_detail', args=[self.id, self.slug])

    def __str__(self):
        start_time_formatted = self.start_time.strftime("%I:%M %p")
        return f"{self.category} - {dict(self.DAY_CHOICES).get(self.day_of_week)} - {start_time_formatted}"

    def create_default_variants(self):
        default_variants = ['Adult', 'Child', 'OAP', 'Student', 'Infant']
        for variant_name in default_variants:
            # Check if the variant already exists for this product
            if not PriceVariant.objects.filter(product=self, variant=variant_name).exists():
                PriceVariant.objects.create(
                    product=self,
                    variant=variant_name,
                    price=9.0  # You can set different prices for each if needed
                )


@receiver(pre_save, sender=PublicSwimProduct)
def update_product_name_and_slug(sender, instance, **kwargs):
    instance.name = instance.generate_name()
    instance.slug = slugify(instance.name)


@receiver(post_save, sender=PublicSwimProduct)
def create_default_variants(sender, instance, created, **kwargs):
    if created:
        instance.create_default_variants()


# Handle Varients for each product
# Prices for OAP, Children etc.
class PriceVariant(models.Model):
    VARIANT_CHOICES = [
        ('Adult', 'Adult'),
        ('Child', 'Child'),
        ('OAP', 'OAP'),
        ('Student', 'Student'),
        ('Infant', 'Infant'),
    ]
    product = models.ForeignKey(PublicSwimProduct, on_delete=models.CASCADE,
                                related_name='price_variants')
    variant = models.CharField(max_length=10, choices=VARIANT_CHOICES,
                               blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, )

    class Meta:
        unique_together = ('product', 'variant')

    def __str__(self):
        return f'{self.product.name} - {self.variant}'

    def get_price(self):
        return self.price
