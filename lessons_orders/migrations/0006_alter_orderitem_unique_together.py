# Generated by Django 4.2.3 on 2024-04-25 18:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_rename_notes_user_admin_notes'),
        ('lessons', '0004_delete_area'),
        ('lessons_orders', '0005_alter_order_amount'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='orderitem',
            unique_together={('order', 'product', 'swimling')},
        ),
    ]
