# Generated by Django 4.2.3 on 2024-05-19 08:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('waiting_list', '0003_waitinglist_assigned_lesson'),
    ]

    operations = [
        migrations.AddField(
            model_name='waitinglist',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
