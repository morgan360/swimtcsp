# Generated by Django 4.2.3 on 2024-05-03 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools_bookings', '0005_alter_scoterm_school'),
    ]

    operations = [
        migrations.AddField(
            model_name='scoterm',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]