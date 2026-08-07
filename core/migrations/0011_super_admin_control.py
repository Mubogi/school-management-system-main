# Generated manually for super admin control system

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_fees_promotion_term_archive'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolconfiguration',
            name='current_term_locked',
            field=models.BooleanField(default=False, help_text='When True, academic records for the active term cannot be edited'),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='academic_period_type',
            field=models.CharField(choices=[('TERMS', 'Terms (e.g. 3 per year)'), ('SEMESTERS', 'Semesters (e.g. 2 per year)')], default='TERMS', max_length=12),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='periods_per_year',
            field=models.PositiveSmallIntegerField(default=3, help_text='Number of terms or semesters per academic year'),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='grading_system',
            field=models.CharField(choices=[('UGCE', 'Uganda UCE (D1–F9)'), ('LETTER', 'Letter grades (A–F)')], default='UGCE', max_length=10),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='label_class',
            field=models.CharField(blank=True, default='Class', max_length=40),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='label_subject',
            field=models.CharField(blank=True, default='Subject', max_length=40),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='label_head_teacher',
            field=models.CharField(blank=True, default='Head Teacher', max_length=60),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='label_dos',
            field=models.CharField(blank=True, default='Director of Studies', max_length=60),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='label_bursar',
            field=models.CharField(blank=True, default='Bursar', max_length=60),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='label_secretary',
            field=models.CharField(blank=True, default='Secretary', max_length=60),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='feature_student_photos',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='feature_reports',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='feature_payments',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='feature_marks_entry',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='feature_promotion',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='feature_notifications',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schoolconfiguration',
            name='carry_fees_on_term_close',
            field=models.BooleanField(default=True, help_text='Outstanding fee demands carry forward when a term is closed'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Inactive users cannot log in'),
        ),
        migrations.AddField(
            model_name='schooltermarchive',
            name='records_locked',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='schooltermarchive',
            name='fees_carried_forward',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='classpromotionrule',
            name='pass_mark',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Minimum average (%) to promote from this class; uses school default if blank', max_digits=5, null=True),
        ),
    ]
