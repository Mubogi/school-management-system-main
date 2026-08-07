# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_report_workflow_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolconfiguration',
            name='address',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='bursar_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='dos_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='fees_demanded',
            field=models.BooleanField(default=False, help_text='Fee demand notices have been issued for the current term'),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='fees_demanded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='head_teacher_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='motto',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='term_open_for_academics',
            field=models.BooleanField(default=True, help_text='When False, mark entry is blocked until bursar opens the term'),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='term_opened_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='website',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='feepaymentledger',
            name='payment_mode',
            field=models.CharField(
                choices=[
                    ('CASH', 'Cash'),
                    ('MOBILE_MONEY', 'Mobile Money'),
                    ('BANK', 'Bank Deposit'),
                    ('CHEQUE', 'Cheque'),
                    ('OTHER', 'Other'),
                ],
                default='CASH',
                max_length=20,
            ),
        ),
    ]
