# Generated migration for Google Drive OAuth backup fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_subjects_backup_enrollment'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolconfiguration',
            name='backup_google_refresh_token',
            field=models.TextField(blank=True, default='', help_text='OAuth2 refresh token for automated Drive uploads'),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='backup_google_folder_id',
            field=models.CharField(blank=True, default='', help_text='Google Drive folder ID for backups', max_length=120),
        ),
    ]
