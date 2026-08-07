"""Bulk mark entry and CSV import/export."""
import csv
import io
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import MarkEntry, Student, Subject, AssessmentType
from .report_services import assert_mark_editable, MarksLockedError


def students_for_bulk(school, class_name):
    return Student.objects.filter(
        school=school, current_class=class_name, is_active=True
    ).order_by('last_name', 'first_name')


def save_bulk_marks(school, class_name, subject, assessment, scores_by_student_id, profile, term, year):
    """scores_by_student_id: dict student_id -> score (Decimal or None to skip)."""
    saved = 0
    errors = []
    for student_id, score in scores_by_student_id.items():
        if score is None or score == '':
            continue
        try:
            student = Student.objects.get(student_id=student_id, school=school, current_class=class_name)
        except Student.DoesNotExist:
            errors.append(f'Unknown student: {student_id}')
            continue
        try:
            assert_mark_editable(student, assessment, term, year)
        except MarksLockedError as exc:
            errors.append(str(exc))
            break
        try:
            score_val = Decimal(str(score))
            if score_val < 0 or score_val > 100:
                errors.append(f'{student_id}: score must be 0–100')
                continue
        except (InvalidOperation, ValueError):
            errors.append(f'{student_id}: invalid score')
            continue

        MarkEntry.objects.update_or_create(
            student=student,
            subject=subject,
            assessment_type=assessment,
            grading_term=term,
            academic_year=year,
            defaults={
                'score_achieved': score_val,
                'recorded_by': profile,
            },
        )
        saved += 1
    return saved, errors


def marks_csv_export(school, class_name, subject, assessment, term, year):
    """Return CSV string for class marksheet template."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'student_id', 'first_name', 'last_name', 'class', 'subject', 'assessment',
        'term', 'academic_year', 'score',
    ])
    students = students_for_bulk(school, class_name)
    existing = {
        row['student__student_id']: row['score_achieved']
        for row in MarkEntry.objects.filter(
            student__in=students,
            subject=subject,
            assessment_type=assessment,
            grading_term=term,
            academic_year=year,
        ).values('student__student_id', 'score_achieved')
    }
    for s in students:
        writer.writerow([
            s.student_id,
            s.first_name,
            s.last_name,
            s.current_class,
            subject.name,
            assessment.name,
            term,
            year,
            existing.get(s.student_id, ''),
        ])
    return output.getvalue()


def marks_csv_import(uploaded_file, school, profile):
    """
    Parse uploaded CSV. Returns (saved_count, errors_list).
    Expected columns: student_id, score (minimum). Optional: subject, assessment, term, academic_year
    """
    decoded = uploaded_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames or 'student_id' not in reader.fieldnames:
        return 0, ['CSV must include a student_id column']

    saved = 0
    errors = []
    term = school.active_term
    year = school.active_academic_year

    with transaction.atomic():
        for i, row in enumerate(reader, start=2):
            student_id = (row.get('student_id') or '').strip()
            if not student_id:
                continue
            try:
                student = Student.objects.get(student_id=student_id, school=school)
            except Student.DoesNotExist:
                errors.append(f'Row {i}: student {student_id} not found')
                continue

            subject_name = (row.get('subject') or '').strip()
            assessment_name = (row.get('assessment') or '').strip()
            row_term = (row.get('term') or term).strip()
            row_year = (row.get('academic_year') or year).strip()

            if subject_name:
                subject = Subject.objects.filter(
                    school=school, name=subject_name, class_level=student.current_class
                ).first()
            else:
                subject = None
            if not subject and row.get('subject_id'):
                subject = Subject.objects.filter(pk=row.get('subject_id'), school=school).first()

            if assessment_name:
                assessment = AssessmentType.objects.filter(school=school, name=assessment_name).first()
            else:
                assessment = None
            if not assessment and row.get('assessment_id'):
                assessment = AssessmentType.objects.filter(pk=row.get('assessment_id'), school=school).first()

            if not subject or not assessment:
                errors.append(f'Row {i}: subject/assessment not found')
                continue

            score_raw = (row.get('score') or '').strip()
            if score_raw == '':
                continue

            try:
                assert_mark_editable(student, assessment, row_term, row_year)
            except MarksLockedError as exc:
                errors.append(f'Row {i}: {exc}')
                continue

            try:
                score_val = Decimal(score_raw)
            except InvalidOperation:
                errors.append(f'Row {i}: invalid score')
                continue

            MarkEntry.objects.update_or_create(
                student=student,
                subject=subject,
                assessment_type=assessment,
                grading_term=row_term,
                academic_year=row_year,
                defaults={'score_achieved': score_val, 'recorded_by': profile},
            )
            saved += 1

    return saved, errors
