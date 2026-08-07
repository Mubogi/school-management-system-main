from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_feestructure_fee_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttermrecord',
            name='dos_remark',
            field=models.TextField(blank=True, default=''),
        ),
    ]
