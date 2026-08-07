from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_school_letterhead_payments_term'),
    ]

    operations = [
        migrations.AddField(
            model_name='feestructure',
            name='fee_type',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Fee type or category',
                max_length=120,
            ),
        ),
    ]
