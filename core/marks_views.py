"""Bulk marks entry and CSV views."""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView

from .marks_bulk import save_bulk_marks, marks_csv_export, marks_csv_import, students_for_bulk
from .models import SchoolClass, Subject, AssessmentType, Student, MarkEntry
from .views import RoleRequiredMixin, get_profile, teacher_can_enter_mark, get_user_school
from .role_access import user_has_role
from .school_config_utils import can_edit_term_records, feature_enabled, is_term_locked


class MarksBulkEntryView(RoleRequiredMixin, TemplateView):
    template_name = 'core/marks/bulk_entry.html'
    allowed_roles = ['SECRETARY', 'DOS', 'CLASS_TEACHER', 'SUBJECT_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile) if profile else None
        if profile and get_user_school(profile):
            school = get_user_school(profile)
            ctx['classes'] = SchoolClass.objects.filter(school=school)
            ctx['subjects'] = Subject.objects.filter(school=school)
            ctx['assessments'] = AssessmentType.objects.filter(school=school)
            ctx['term'] = school.active_term
            ctx['year'] = school.active_academic_year
            ctx['term_open'] = school.term_open_for_academics and not is_term_locked(school)
            ctx['term_locked'] = is_term_locked(school)

            class_name = self.request.GET.get('class')
            subject_id = self.request.GET.get('subject')
            assessment_id = self.request.GET.get('assessment')
            if class_name and subject_id and assessment_id:
                subject = get_object_or_404(Subject, pk=subject_id, school=school)
                assessment = get_object_or_404(AssessmentType, pk=assessment_id, school=school)
                ctx['selected_class'] = class_name
                ctx['selected_subject'] = subject
                ctx['selected_assessment'] = assessment
                students = students_for_bulk(school, class_name)
                existing = {
                    row['student__student_id']: row['score_achieved']
                    for row in MarkEntry.objects.filter(
                        student__in=students,
                        subject=subject,
                        assessment_type=assessment,
                        grading_term=ctx['term'],
                        academic_year=ctx['year'],
                    ).values('student__student_id', 'score_achieved')
                }
                ctx['student_rows'] = [
                    {'student': s, 'score': existing.get(s.student_id, '')}
                    for s in students
                ]
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not get_user_school(profile):
            raise Http404()
        school = get_user_school(profile)

        if not school.term_open_for_academics:
            messages.error(request, 'Term is not open for mark entry. Ask the bursar to open the term after fee demands.')
            return redirect('core:marks_bulk_entry')

        if not can_edit_term_records(profile, school):
            messages.error(request, 'This term is closed. Records cannot be edited.')
            return redirect('core:marks_bulk_entry')

        if not feature_enabled(school, 'marks_entry'):
            messages.error(request, 'Marks entry is disabled for this school.')
            return redirect('core:marks_bulk_entry')

        class_name = request.POST.get('class_name')
        subject = get_object_or_404(Subject, pk=request.POST.get('subject_id'), school=school)
        assessment = get_object_or_404(AssessmentType, pk=request.POST.get('assessment_id'), school=school)
        term = request.POST.get('term') or school.active_term
        year = request.POST.get('year') or school.active_academic_year

        scores = {}
        for key, val in request.POST.items():
            if key.startswith('score_'):
                sid = key.replace('score_', '', 1)
                scores[sid] = val

        saved, errors = save_bulk_marks(
            school, class_name, subject, assessment, scores, profile, term, year
        )
        if errors:
            for e in errors[:5]:
                messages.error(request, e)
        if saved:
            messages.success(request, f'Saved {saved} mark(s) for {assessment.name}.')
        return redirect(
            reverse('core:marks_bulk_entry')
            + f'?class={class_name}&subject={subject.pk}&assessment={assessment.pk}'
        )


def marks_csv_download(request):
    profile = get_profile(request.user)
    if not user_has_role(profile, ['SECRETARY', 'DOS', 'CLASS_TEACHER', 'SUBJECT_TEACHER']):
        raise Http404()
    school = get_user_school(profile)
    class_name = request.GET.get('class')
    subject_pk = request.GET.get('subject')
    assessment_pk = request.GET.get('assessment')
    # Missing required params — redirect to bulk entry instead of 404
    if not subject_pk or not assessment_pk:
        messages.error(request, 'Select a subject and assessment to download marks.')
        return redirect('core:marks_bulk_entry')
    subject = get_object_or_404(Subject, pk=subject_pk, school=school)
    assessment = get_object_or_404(AssessmentType, pk=assessment_pk, school=school)
    term = request.GET.get('term') or school.active_term
    year = request.GET.get('year') or school.active_academic_year

    csv_data = marks_csv_export(school, class_name, subject, assessment, term, year)
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{class_name}_{subject.name}_{assessment.name}_marks.csv"'
    )
    return response


def marks_csv_upload(request):
    profile = get_profile(request.user)
    if not user_has_role(profile, ['SECRETARY', 'DOS', 'CLASS_TEACHER', 'SUBJECT_TEACHER']):
        raise Http404()
    if request.method != 'POST':
        # GET on an upload action endpoint — send back to the bulk entry page
        return redirect('core:marks_bulk_entry')
    school = get_user_school(profile)
    if not school.term_open_for_academics:
        messages.error(request, 'Term is not open for mark entry.')
        return redirect('core:marks_bulk_entry')
    if not can_edit_term_records(profile, school):
        messages.error(request, 'This term is closed. Records cannot be edited.')
        return redirect('core:marks_bulk_entry')

    f = request.FILES.get('csv_file')
    if not f:
        messages.error(request, 'Choose a CSV file to upload.')
        return redirect('core:marks_bulk_entry')

    saved, errors = marks_csv_import(f, school, profile)
    if errors:
        for e in errors[:8]:
            messages.error(request, e)
    if saved:
        messages.success(request, f'Imported {saved} mark(s) from CSV.')
    elif not errors:
        messages.warning(request, 'No marks were imported.')
    return redirect('core:marks_bulk_entry')
