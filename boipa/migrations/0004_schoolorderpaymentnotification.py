# Generated by Django 4.2.3 on 2024-04-09 10:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schools_orders', '0001_initial'),
        ('boipa', '0003_rename_paymentnotification_lessonorderpaymentnotification_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolOrderPaymentNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txId', models.CharField(max_length=50)),
                ('merchantTxId', models.CharField(max_length=50)),
                ('country', models.CharField(blank=True, max_length=2, null=True)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('currency', models.CharField(blank=True, max_length=3, null=True)),
                ('action', models.CharField(blank=True, max_length=10, null=True)),
                ('auth_code', models.CharField(blank=True, max_length=10, null=True)),
                ('acquirer', models.CharField(blank=True, max_length=100, null=True)),
                ('acquirerAmount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('merchantId', models.CharField(blank=True, max_length=50, null=True)),
                ('brandId', models.CharField(blank=True, max_length=50, null=True)),
                ('customerId', models.CharField(max_length=50, null=True)),
                ('acquirerCurrency', models.CharField(blank=True, max_length=3, null=True)),
                ('paymentSolutionId', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='schools_orders.order')),
            ],
        ),
    ]