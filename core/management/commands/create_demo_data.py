from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (
    SchoolConfiguration, UserProfile, AssessmentType, FeeStructure, Student,
    SchoolClass, Subject, FeeComponent, FeePaymentLedger, MarkEntry,
    ClassTeacherAssignment, TeacherSubjectAssignment
)
from decimal import Decimal
from datetime import date
import random


class Command(BaseCommand):
    help = 'Create demo school and users for all roles'

    def handle(self, *args, **options):
        # Create demo school
        school, created = SchoolConfiguration.objects.get_or_create(
            school_name='Demo Academy',
            defaults={
                'school_initials_prefix': 'DEMO',
                'active_academic_year': '2026',
                'active_term': 'T1',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created school: {school.school_name}'))
        else:
            self.stdout.write(f'School already exists: {school.school_name}')

        # Define roles
        roles = [
            ('super_admin', 'SUPER_ADMIN', 'Super Admin'),
            ('admin1', 'SCHOOL_ADMIN', 'School Admin'),
            ('dos1', 'DOS', 'Director of Studies'),
            ('secretary1', 'SECRETARY', 'Secretary'),
            ('bursar1', 'BURSAR', 'Bursar'),
            ('teacher1', 'CLASS_TEACHER', 'Class Teacher'),
            ('subject_teacher1', 'SUBJECT_TEACHER', 'Subject Teacher'),
            ('head_teacher1', 'HEAD_TEACHER', 'Head Teacher'),
        ]

        for username, role_key, role_display in roles:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@demo.school',
                    'first_name': role_display,
                    'last_name': 'Demo',
                }
            )
            if created:
                user.set_password('password')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created user: {username} (password: password)'))
            else:
                user.set_password('password')
                user.save()
                self.stdout.write(f'  Updated user: {username} (password: password)')

            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'school': school,
                    'role': role_key,
                }
            )
            if created:
                self.stdout.write(f'    ✓ Created profile with role: {role_display}')
            else:
                profile.school = school
                profile.role = role_key
                profile.save()
                self.stdout.write(f'    Updated profile with role: {role_display}')

        classes = ['Form 1A', 'Form 2A', 'Form 3A', 'Form 4A']
        class_map = {}
        for class_name in classes:
            school_class, _ = SchoolClass.objects.get_or_create(school=school, name=class_name)
            class_map[class_name] = school_class

        subjects = [
            ('English', 'Form 1A'),
            ('Mathematics', 'Form 1A'),
            ('Biology', 'Form 2A'),
            ('Chemistry', 'Form 2A'),
            ('Physics', 'Form 3A'),
            ('History', 'Form 3A'),
            ('Geography', 'Form 4A'),
            ('Computer Studies', 'Form 4A'),
        ]
        subject_map = {}
        for name, level in subjects:
            subject, _ = Subject.objects.get_or_create(school=school, name=name, class_level=level)
            subject_map[f'{name}-{level}'] = subject

        assessment_types = [
            ('Mid-Term Test', 20),
            ('End of Term Exam', 40),
            ('Class Work', 15),
            ('Practicals', 25),
        ]
        assessment_map = {}
        for name, weight in assessment_types:
            assessment, _ = AssessmentType.objects.get_or_create(
                name=name,
                school=school,
                defaults={'weight_percentage': weight}
            )
            assessment_map[name] = assessment

        fees_data = [
            ('Form 1A', 'T1', '2026', Decimal('50000.00')),
            ('Form 2A', 'T1', '2026', Decimal('55000.00')),
            ('Form 3A', 'T1', '2026', Decimal('60000.00')),
            ('Form 4A', 'T1', '2026', Decimal('65000.00')),
        ]
        for target_class, term, year, amount in fees_data:
            fee_structure, created = FeeStructure.objects.get_or_create(
                school=school,
                target_class=target_class,
                term=term,
                academic_year=year,
                defaults={'total_fees_required': amount, 'school_class': class_map[target_class]}
            )
            if created:
                FeeComponent.objects.create(fee_structure=fee_structure, name='Tuition', amount=(amount * Decimal('0.70')).quantize(Decimal('0.01')))
                FeeComponent.objects.create(fee_structure=fee_structure, name='Lab & Exam', amount=(amount * Decimal('0.20')).quantize(Decimal('0.01')))
                FeeComponent.objects.create(fee_structure=fee_structure, name='Library & Activities', amount=(amount * Decimal('0.10')).quantize(Decimal('0.01')))
                self.stdout.write(self.style.SUCCESS(f'✓ Created fee structure: {target_class} - {term} {year} (Ushs {amount})')

        student_profiles = [
            ('Alice', 'Njeri', 'Form 1A'),
            ('Brian', 'Otieno', 'Form 1A'),
            ('Catherine', 'Wanjiru', 'Form 2A'),
            ('David', 'Kimani', 'Form 2A'),
            ('Esther', 'Mutua', 'Form 3A'),
            ('Francis', 'Maina', 'Form 3A'),
            ('Grace', 'Achieng', 'Form 4A'),
            ('Henry', 'Ouma', 'Form 4A'),
            ('Irene', 'Mburu', 'Form 1A'),
            ('James', 'Mwangi', 'Form 2A'),
            ('Katherine', 'Wambui', 'Form 3A'),
            ('Leon', 'Kamau', 'Form 4A'),
        ]

        demo_students = []
        for first_name, last_name, current_class in student_profiles:
            student, created = Student.objects.get_or_create(
                school=school,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date(2008, random.randint(1, 12), random.randint(1, 28)),
                defaults={
                    'gender': random.choice(['M', 'F']),
                    'current_class': current_class,
                    'guardian_name': f'{last_name} Family',
                    'guardian_phone': f'+2547{random.randint(10000000, 99999999)}',
                    'guardian_email': f'{first_name.lower()}.{last_name.lower()}@demo.school',
                    'address': 'Demo Street, Demo City',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created student: {student.first_name} {student.last_name} (ID: {student.student_id})'))
            demo_students.append(student)

        teacher_profile = UserProfile.objects.filter(school=school, role='CLASS_TEACHER').first()
        subject_teacher_profile = UserProfile.objects.filter(school=school, role='SUBJECT_TEACHER').first()
        if teacher_profile and class_map.get('Form 1A'):
            ClassTeacherAssignment.objects.get_or_create(teacher=teacher_profile, school_class=class_map['Form 1A'])
        if subject_teacher_profile and subject_map.get('English-Form 1A'):
            TeacherSubjectAssignment.objects.get_or_create(
                teacher=subject_teacher_profile,
                subject=subject_map['English-Form 1A'],
                assigned_class='Form 1A'
            )

        for student in demo_students:
            fee_struct = student.get_fee_structure()
            if fee_struct:
                amount = fee_struct.compute_total()
                paid = Decimal(random.choice([0, amount * Decimal('0.20'), amount * Decimal('0.50'), amount * Decimal('0.80')])).quantize(Decimal('0.01'))
                if paid > 0:
                    FeePaymentLedger.create_payment(student=student, amount=paid, recorded_by=profile)

            for subject in Subject.objects.filter(school=school, class_level=student.current_class):
                for assessment in assessment_map.values():
                    score = Decimal(random.randint(45, 95))
                    MarkEntry.objects.get_or_create(
                        student=student,
                        subject=subject,
                        assessment_type=assessment,
                        grading_term=school.active_term,
                        academic_year=school.active_academic_year,
                        defaults={
                            'score_achieved': score,
                            'recorded_by': subject_teacher_profile,
                        }
                    )

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('DEMO DATA CREATED SUCCESSFULLY!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('\nLogin Credentials:')
        self.stdout.write(f'  School Initials: DEMO')
        self.stdout.write(f'  Password: password')
        self.stdout.write('\nUsers:')
        for username, role_key, role_display in roles:
            self.stdout.write(f'  ✓ {username:20} ({role_display})')
        self.stdout.write('\n' + '='*60 + '\n')
