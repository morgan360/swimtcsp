# Generated by Django 4.2.3 on 2024-04-25 18:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0004_delete_scoarea'),
    ]

    operations = [
        migrations.RenameField(
            model_name='scoschool',
            old_name='sco_name',
            new_name='name',
        ),
    ]