# Generated by Django 4.2.3 on 2023-08-13 11:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lessons_bookings', '0003_remove_lessonenrollment_order'),
        ('lessons_orders', '0003_orderitem_swimling'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='term',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='lessons_bookings.term'),
        ),
    ]