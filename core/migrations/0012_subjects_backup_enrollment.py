# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_super_admin_control'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='subject_type',
            field=models.CharField(
                choices=[('COMPULSORY', 'Compulsory (whole class)'), ('OPTIONAL', 'Optional (per student)')],
                default='COMPULSORY', max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='backup_google_drive_url',
            field=models.URLField(blank=True, default='', help_text='Permanent Google Drive folder link for backups'),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='backup_auto_sync_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='backup_auto_sync_days',
            field=models.PositiveSmallIntegerField(default=7),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='backup_last_export_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='network_app_name',
            field=models.CharField(blank=True, default='OfficeHub School', max_length=80),
        ),
        migrations.CreateModel(
            name='StudentSubjectEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subject_enrollments', to='core.student')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_enrollments', to='core.subject')),
            ],
            options={
                'ordering': ['subject__name'],
                'unique_together': {('student', 'subject')},
            },
        ),
    ]
