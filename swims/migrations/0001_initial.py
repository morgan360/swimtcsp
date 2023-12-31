# Generated by Django 4.2.3 on 2023-08-23 15:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PriceVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variant', models.CharField(blank=True, choices=[('Adult', 'Adult'), ('Child', 'Child'), ('OAP', 'OAP'), ('Student', 'Student')], max_length=10)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PublicSwimCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, null=True)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Public Swim Category',
                'verbose_name_plural': 'Public Swim Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PublicSwimProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True)),
                ('slug', models.SlugField(blank=True, max_length=200)),
                ('start_time', models.TimeField(blank=True)),
                ('end_time', models.TimeField(blank=True)),
                ('day_of_week', models.PositiveSmallIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('num_places', models.IntegerField(null=True)),
                ('available', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(default='images/default_image.jpg', upload_to='products/%Y/%m/%d')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='swims.publicswimcategory')),
            ],
            options={
                'verbose_name': 'Public Swim',
                'verbose_name_plural': 'Public Swims',
                'ordering': ['day_of_week'],
            },
        ),
        migrations.AddIndex(
            model_name='publicswimcategory',
            index=models.Index(fields=['name'], name='swims_publi_name_e8fdd8_idx'),
        ),
        migrations.AddField(
            model_name='pricevariant',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_variants', to='swims.publicswimproduct'),
        ),
    ]
