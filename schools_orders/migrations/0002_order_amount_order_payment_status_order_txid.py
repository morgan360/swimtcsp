# Generated by Django 4.2.3 on 2024-04-10 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools_orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='txId',
            field=models.CharField(blank=True, max_length=250),
        ),
    ]
