from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_userprofile_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='feepaymentledger',
            name='academic_year',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
        migrations.AddField(
            model_name='feepaymentledger',
            name='term',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
    ]
