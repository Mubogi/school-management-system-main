"""Persist student and optional subject enrollments."""
from .models import StudentSubjectEnrollment


def persist_student_from_form(form, school):
    student = form.save(commit=False)
    student.school = school
    student.save()
    if hasattr(form, 'save_optional_subjects'):
        form.save_optional_subjects(student)
    return student


def update_student_optional_subjects(student, subject_ids):
    StudentSubjectEnrollment.objects.filter(student=student).update(is_active=False)
    for sid in subject_ids:
        StudentSubjectEnrollment.objects.update_or_create(
            student=student, subject_id=sid,
            defaults={'is_active': True},
        )
