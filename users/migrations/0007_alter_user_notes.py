# Generated by Django 4.2.3 on 2023-09-14 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_remove_userprofile_home_phone_user_other_phone_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
