# Generated by Django 4.2.3 on 2023-08-24 18:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swimling',
            name='dob',
            field=models.DateField(blank=True, null=True),
        ),
    ]