# Generated by Django 4.2.3 on 2024-04-10 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lessons_orders', '0003_rename_stripe_id_order_txid_order_amount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
