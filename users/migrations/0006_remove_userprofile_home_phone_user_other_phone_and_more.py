# Generated by Django 4.2.3 on 2023-09-01 15:06

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_rename_school_role_number_swimling_sco_role_num'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='home_phone',
        ),
        migrations.AddField(
            model_name='user',
            name='other_phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region=None),
        ),
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='notes',
            field=models.TextField(),
        ),
    ]
