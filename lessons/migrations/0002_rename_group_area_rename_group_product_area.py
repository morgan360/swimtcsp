# Generated by Django 4.2.3 on 2023-09-02 18:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lessons', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Group',
            new_name='Area',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='group',
            new_name='area',
        ),
    ]
