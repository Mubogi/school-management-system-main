# Generated manually for report workflow features

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_feepaymentledger_term_year'),
    ]

    operations = [
        migrations.CreateModel(
            name='TermReportPublication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_name', models.CharField(blank=True, default='', help_text='Blank = entire school', max_length=50)),
                ('term', models.CharField(max_length=10)),
                ('academic_year', models.CharField(max_length=10)),
                ('report_type', models.CharField(choices=[('midterm', 'Mid-Term'), ('eot', 'End of Term')], max_length=10)),
                ('is_published', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('published_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.userprofile')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_publications', to='core.schoolconfiguration')),
            ],
            options={
                'ordering': ['-published_at'],
                'unique_together': {('school', 'class_name', 'term', 'academic_year', 'report_type')},
            },
        ),
        migrations.CreateModel(
            name='StudentTermRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(max_length=10)),
                ('academic_year', models.CharField(max_length=10)),
                ('days_present', models.PositiveIntegerField(default=0)),
                ('total_school_days', models.PositiveIntegerField(default=60, help_text='Total school days in the term')),
                ('conduct_rating', models.CharField(choices=[('EXCELLENT', 'Excellent'), ('GOOD', 'Good'), ('FAIR', 'Fair'), ('NEEDS_IMPROVEMENT', 'Needs Improvement')], default='GOOD', max_length=20)),
                ('conduct_note', models.TextField(blank=True, default='')),
                ('class_teacher_remark', models.TextField(blank=True, default='')),
                ('head_teacher_remark', models.TextField(blank=True, default='')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='term_records', to='core.student')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.userprofile')),
            ],
            options={
                'ordering': ['student__last_name'],
                'unique_together': {('student', 'term', 'academic_year')},
            },
        ),
        migrations.CreateModel(
            name='ClassPromotionRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_class', models.CharField(max_length=50)),
                ('to_class', models.CharField(blank=True, default='', help_text='Leave blank to mark students as graduated', max_length=50)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotion_rules', to='core.schoolconfiguration')),
            ],
            options={
                'ordering': ['from_class'],
                'unique_together': {('school', 'from_class')},
            },
        ),
        migrations.CreateModel(
            name='PromotionRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_academic_year', models.CharField(max_length=10)),
                ('to_academic_year', models.CharField(max_length=10)),
                ('students_promoted', models.PositiveIntegerField(default=0)),
                ('students_graduated', models.PositiveIntegerField(default=0)),
                ('run_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('run_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.userprofile')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotion_runs', to='core.schoolconfiguration')),
            ],
        ),
        migrations.CreateModel(
            name='ReportNotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(max_length=10)),
                ('academic_year', models.CharField(max_length=10)),
                ('report_type', models.CharField(max_length=10)),
                ('channel', models.CharField(choices=[('email', 'Email'), ('sms', 'SMS')], max_length=10)),
                ('recipient', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')], max_length=10)),
                ('detail', models.TextField(blank=True, default='')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.userprofile')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_notifications', to='core.student')),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
    ]
