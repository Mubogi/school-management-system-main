from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_studenttermrecord_dos_remark'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='feestructure',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='feepaymentledger',
            name='fee_type',
            field=models.CharField(blank=True, default='', help_text='Fee category this payment applies to', max_length=120),
        ),
        migrations.AlterUniqueTogether(
            name='feestructure',
            unique_together={('school', 'target_class', 'term', 'academic_year', 'fee_type')},
        ),
        migrations.CreateModel(
            name='StudentFeeCredit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('fee_type', models.CharField(blank=True, default='', max_length=120)),
                ('term', models.CharField(max_length=10)),
                ('academic_year', models.CharField(max_length=10)),
                ('notes', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_credits', to='core.student')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromotionCriteria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minimum_average', models.DecimalField(decimal_places=2, default=Decimal('50.00'), help_text='Minimum overall average (%) to qualify for promotion', max_digits=5)),
                ('require_fees_cleared', models.BooleanField(default=False)),
                ('minimum_attendance_percent', models.PositiveIntegerField(default=75, help_text='Minimum attendance % required for promotion')),
                ('auto_promote_on_year_end', models.BooleanField(default=False, help_text='When enabled, year-end promotion skips students below pass mark')),
                ('school', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='promotion_criteria', to='core.schoolconfiguration')),
            ],
        ),
        migrations.CreateModel(
            name='SchoolTermArchive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(max_length=10)),
                ('academic_year', models.CharField(max_length=10)),
                ('closed_at', models.DateTimeField(auto_now_add=True)),
                ('reports_published', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, default='')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='term_archives', to='core.schoolconfiguration')),
                ('closed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.userprofile')),
            ],
            options={
                'ordering': ['-closed_at'],
                'unique_together': {('school', 'term', 'academic_year')},
            },
        ),
    ]
