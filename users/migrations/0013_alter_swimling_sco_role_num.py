# Generated by Django 4.2.3 on 2024-05-07 12:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_alter_swimling_sco_role_num'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swimling',
            name='sco_role_num',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
    ]
