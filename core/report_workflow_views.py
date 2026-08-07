"""Views for publish/lock, remarks, notifications, and promotion."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.http import Http404

from licensing.decorators import feature_required

from .models import (
    Student, SchoolClass, ClassTeacherAssignment, StudentTermRecord,
    ClassPromotionRule, PromotionRun, ReportNotificationLog,
    TermReportPublication,
)
from .forms import (
    StudentTermRecordForm, ClassPromotionRuleForm, PromotionRunForm, ReportNotifyForm,
)
from .report_services import (
    publish_reports, unpublish_reports, publication_status_for_classes,
    get_or_init_term_record, send_report_email, send_report_sms,
    send_bulk_report_emails,
    promotion_preview, run_year_end_promotion, is_report_published,
)
from .report_utils import normalize_report_type, REPORT_MID_TERM
from .views import (
    RoleRequiredMixin, get_profile, get_user_school,
)

from licensing.models import AuditLog


class HeadTeacherPublishReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/head_teacher/publish_reports.html'
    allowed_roles = ['HEAD_TEACHER', 'SCHOOL_ADMIN', 'SUPER_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile) if profile else None
        if profile and get_user_school(profile):
            school = get_user_school(profile)
            term = self.request.GET.get('term') or school.active_term
            year = self.request.GET.get('year') or school.active_academic_year
            ctx['term'] = term
            ctx['academic_year'] = year
            ctx['class_rows'], ctx['whole_school'] = publication_status_for_classes(school, term, year)
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not get_user_school(profile):
            raise Http404()
        school = get_user_school(profile)
        action = request.POST.get('action')
        class_name = request.POST.get('class_name', '')
        term = request.POST.get('term') or school.active_term
        year = request.POST.get('year') or school.active_academic_year
        report_type = normalize_report_type(request.POST.get('report_type'))

        if action == 'publish':
            publish_reports(school, class_name, term, year, report_type, profile)
            scope = class_name or 'whole school'
            messages.success(request, f'Published {report_type} reports for {scope}. Marks for those assessments are now locked.')
        elif action == 'unpublish':
            unpublish_reports(school, class_name, term, year, report_type, profile)
            scope = class_name or 'whole school'
            messages.success(request, f'Unlocked {report_type} reports for {scope}. Marks can be edited again.')
        else:
            messages.error(request, 'Unknown action.')

        from django.urls import reverse
        return redirect(reverse('core:head_teacher_publish') + f'?term={term}&year={year}')


class ClassTeacherRemarksView(RoleRequiredMixin, TemplateView):
    template_name = 'core/class_teacher/remarks.html'
    allowed_roles = ['CLASS_TEACHER', 'HEAD_TEACHER', 'DOS', 'SUPER_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile) if profile else None
        ctx['can_edit_ht_remarks'] = profile and profile.role in ['HEAD_TEACHER', 'DOS', 'SUPER_ADMIN']
        ctx['can_edit_dos_remarks'] = profile and profile.role in ['DOS', 'SUPER_ADMIN']

        if not profile or not get_user_school(profile):
            return ctx

        school = get_user_school(profile)
        term = self.request.GET.get('term') or school.active_term
        year = self.request.GET.get('year') or school.active_academic_year
        ctx['term'] = term
        ctx['academic_year'] = year

        class_name = self.request.GET.get('class')
        if profile.role == 'CLASS_TEACHER':
            assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
            if not assignment:
                return ctx
            class_name = assignment.school_class.name
        elif profile.role in ['HEAD_TEACHER', 'DOS', 'SUPER_ADMIN'] and not class_name:
            first = SchoolClass.objects.filter(school=school).first()
            class_name = first.name if first else None
        elif not class_name:
            first = SchoolClass.objects.filter(school=school).first()
            class_name = first.name if first else None

        ctx['selected_class'] = class_name
        ctx['classes'] = SchoolClass.objects.filter(school=school)

        if class_name:
            students = Student.objects.filter(
                school=school, current_class=class_name, is_active=True
            ).order_by('last_name')
            rows = []
            for student in students:
                record, _ = get_or_init_term_record(student, term, year)
                rows.append({'student': student, 'record': record, 'form': StudentTermRecordForm(instance=record)})
            ctx['student_rows'] = rows
            ctx['midterm_locked'] = is_report_published(school, class_name, term, year, REPORT_MID_TERM)
            ctx['eot_locked'] = is_report_published(school, class_name, term, year, 'eot')

        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not get_user_school(profile):
            raise Http404()

        student = get_object_or_404(Student, pk=request.POST.get('student_id'), school=get_user_school(profile))
        if profile.role == 'CLASS_TEACHER':
            assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
            if not assignment or assignment.school_class.name != student.current_class:
                raise Http404()

        term = request.POST.get('term') or get_user_school(profile).active_term
        year = request.POST.get('year') or get_user_school(profile).active_academic_year
        record, _ = get_or_init_term_record(student, term, year)
        form = StudentTermRecordForm(request.POST, instance=record)

        if profile.role == 'CLASS_TEACHER':
            form.fields['head_teacher_remark'].disabled = True
            form.fields['dos_remark'].disabled = True
        elif profile.role == 'HEAD_TEACHER':
            form.fields['class_teacher_remark'].disabled = True
            form.fields['dos_remark'].disabled = True
        elif profile.role == 'DOS':
            form.fields['class_teacher_remark'].disabled = True
        # SUPER_ADMIN can edit all fields

        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = profile
            if profile.role == 'CLASS_TEACHER':
                obj.head_teacher_remark = record.head_teacher_remark
                obj.dos_remark = record.dos_remark
            elif profile.role == 'HEAD_TEACHER':
                obj.class_teacher_remark = record.class_teacher_remark
                obj.dos_remark = record.dos_remark
            elif profile.role == 'DOS':
                obj.class_teacher_remark = record.class_teacher_remark
            obj.save()
            messages.success(request, f'Saved report details for {student.first_name} {student.last_name}.')
        else:
            messages.error(request, 'Could not save — please check the form.')

        from django.urls import reverse
        return redirect(
            reverse('core:class_teacher_remarks')
            + f'?class={student.current_class}&term={term}&year={year}'
        )


class ReportNotificationsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/shared/report_notifications.html'
    allowed_roles = ['HEAD_TEACHER', 'DOS', 'SECRETARY', 'CLASS_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile) if profile else None
        ctx['form'] = ReportNotifyForm(school=get_user_school(profile) if profile else None)
        if profile and get_user_school(profile):
            ctx['recent_logs'] = ReportNotificationLog.objects.filter(
                student__school=get_user_school(profile)
            ).select_related('student')[:30]
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not get_user_school(profile):
            raise Http404()

        form = ReportNotifyForm(request.POST, school=get_user_school(profile))
        if not form.is_valid():
            messages.error(request, 'Invalid form.')
            return redirect('core:report_notifications')

        school = get_user_school(profile)
        term = school.active_term
        year = school.active_academic_year
        report_type = normalize_report_type(form.cleaned_data['report_type'])
        class_name = form.cleaned_data['class_name']
        channel = form.cleaned_data['channel']

        students = Student.objects.filter(school=school, is_active=True)
        if class_name:
            students = students.filter(current_class=class_name)
        if profile.role == 'CLASS_TEACHER':
            assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
            if assignment:
                students = students.filter(current_class=assignment.school_class.name)

        sent = failed = skipped = 0
        student_list = list(students)
        if channel in ('email', 'both'):
            bulk_sent = send_bulk_report_emails(student_list, report_type, term, year, request, profile)
            sent += bulk_sent
            skipped += len(student_list) - sum(1 for s in student_list if (s.guardian_email or '').strip())
        if channel in ('sms', 'both'):
            for student in student_list:
                ok, _ = send_report_sms(student, report_type, term, year, request, profile)
                if ok:
                    sent += 1
                else:
                    failed += 1

        messages.success(
            request,
            f'Notifications sent. Emails/SMS queued: {sent}, skipped/failed: {skipped + failed}. '
            f'Emails are composed from the school address ({school.email or "configure in school settings"}).',
        )
        return redirect('core:report_notifications')


class PromotionRulesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dos/promotion_rules.html'
    allowed_roles = ['DOS', 'SCHOOL_ADMIN', 'SUPER_ADMIN', 'HEAD_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile) if profile else None
        if profile and get_user_school(profile):
            ctx['rules'] = ClassPromotionRule.objects.filter(school=get_user_school(profile))
            ctx['rule_form'] = ClassPromotionRuleForm()
            ctx['classes'] = SchoolClass.objects.filter(school=get_user_school(profile))
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not get_user_school(profile):
            raise Http404()

        if request.POST.get('action') == 'delete':
            rule = get_object_or_404(ClassPromotionRule, pk=request.POST.get('rule_id'), school=get_user_school(profile))
            rule.delete()
            messages.success(request, 'Promotion rule removed.')
            return redirect('core:promotion_rules')

        form = ClassPromotionRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.school = get_user_school(profile)
            ClassPromotionRule.objects.update_or_create(
                school=get_user_school(profile),
                from_class=rule.from_class,
                defaults={'to_class': rule.to_class},
            )
            messages.success(request, f'Rule saved: {rule.from_class} → {rule.to_class or "Graduate"}')
        else:
            messages.error(request, 'Invalid rule.')
        return redirect('core:promotion_rules')


class YearEndPromotionView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dos/year_end_promotion.html'
    allowed_roles = ['DOS', 'SCHOOL_ADMIN', 'SUPER_ADMIN', 'HEAD_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile) if profile else None
        if profile and get_user_school(profile):
            ctx['preview'] = promotion_preview(get_user_school(profile))
            try:
                next_year = str(int(get_user_school(profile).active_academic_year) + 1)
            except (TypeError, ValueError):
                next_year = get_user_school(profile).active_academic_year
            ctx['form'] = PromotionRunForm(initial={'to_academic_year': next_year})
            ctx['past_runs'] = PromotionRun.objects.filter(school=get_user_school(profile))[:10]
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not get_user_school(profile):
            raise Http404()

        form = PromotionRunForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please confirm promotion to proceed.')
            return redirect('core:year_end_promotion')

        school = get_user_school(profile)
        result = run_year_end_promotion(
            school,
            form.cleaned_data['to_academic_year'],
            profile,
            reset_term='T1' if form.cleaned_data.get('reset_term') else school.active_term,
        )
        run, promoted, graduated, unchanged = result[:4]
        retained = result[4] if len(result) > 4 else 0
        messages.success(
            request,
            f'Promotion complete for {school.school_name}: {promoted} promoted, '
            f'{graduated} graduated, {retained} retained (below pass mark). '
            f'Active year is now {school.active_academic_year}. '
            f'{unchanged} unchanged (no rule).',
        )
        return redirect('core:year_end_promotion')


class BulkStudentPromotionView(RoleRequiredMixin, TemplateView):
    """
    Bulk promotion view with checkbox selection and dropdown-based class/term selection.
    Allows promoting individual students, moving to archive, or graduating.
    """
    template_name = 'core/dos/bulk_promotion.html'
    allowed_roles = ['DOS', 'SCHOOL_ADMIN', 'SUPER_ADMIN', 'HEAD_TEACHER']
    
    # Predefined class options for dropdowns
    CLASS_OPTIONS = [
        ('P.1', 'P.1'), ('P.2', 'P.2'), ('P.3', 'P.3'), ('P.4', 'P.4'),
        ('P.5', 'P.5'), ('P.6', 'P.6'), ('P.7', 'P.7'),
        ('S.1', 'S.1'), ('S.2', 'S.2'), ('S.3', 'S.3'), ('S.4', 'S.4'),
        ('S.5', 'S.5'), ('S.6', 'S.6'),
    ]
    
    # Predefined term options
    TERM_OPTIONS = [
        ('T1', 'Term 1'), ('T2', 'Term 2'), ('T3', 'Term 3'),
        ('S1', 'Semester 1'), ('S2', 'Semester 2'),
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile) if profile else None
        
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        
        # Get school classes for dropdown
        if school:
            existing_classes = SchoolClass.objects.filter(school=school).values_list('name', flat=True)
            # Combine predefined with existing
            all_classes = list(set(list(self.CLASS_OPTIONS) + [(c, c) for c in existing_classes]))
            ctx['class_options'] = sorted(all_classes, key=lambda x: x[0])
        else:
            ctx['class_options'] = self.CLASS_OPTIONS
        
        ctx['term_options'] = self.TERM_OPTIONS
        
        # Get students for the school
        if school:
            from core.models import Student
            students = Student.objects.filter(
                school=school,
                is_active=True
            ).order_by('current_class', 'last_name')
            
            # Group students by class
            from itertools import groupby
            students_by_class = {}
            for student in students:
                class_name = student.current_class or 'Unassigned'
                if class_name not in students_by_class:
                    students_by_class[class_name] = []
                students_by_class[class_name].append(student)
            
            ctx['students_by_class'] = students_by_class
            ctx['total_students'] = students.count()
        else:
            ctx['students_by_class'] = {}
            ctx['total_students'] = 0
        
        return ctx
    
    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile) if profile else None
        
        if not school:
            messages.error(request, 'No school context found.')
            return redirect('core:bulk_promotion')
        
        action = request.POST.get('action')
        student_ids = request.POST.getlist('student_ids')
        target_class = request.POST.get('target_class', '')
        target_year = request.POST.get('target_academic_year', '')
        target_term = request.POST.get('target_term', school.active_term or 'T1')
        
        from core.models import Student
        from licensing.models import AuditLog
        
        promoted_count = 0
        archived_count = 0
        graduated_count = 0
        
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id, school=school)
                old_class = student.current_class
                
                if action == 'promote':
                    student.current_class = target_class
                    student.save()
                    promoted_count += 1
                    
                    # Log the action
                    AuditLog.log(
                        action='STUDENT_PROMOTE',
                        user=request.user,
                        target_type='Student',
                        target_id=student.student_id,
                        target_name=f"{student.first_name} {student.last_name}",
                        description=f"Promoted from {old_class} to {target_class}",
                        request=request,
                        school=school,
                    )
                    
                elif action == 'archive':
                    student.is_active = False  # Deactivate instead of archiving
                    student.save()
                    archived_count += 1
                    
                    AuditLog.log(
                        action='STUDENT_ARCHIVE',
                        user=request.user,
                        target_type='Student',
                        target_id=student.student_id,
                        target_name=f"{student.first_name} {student.last_name}",
                        description="Student deactivated/archived",
                        request=request,
                        school=school,
                    )
                    
                elif action == 'graduate':
                    student.is_active = False  # Deactivate instead
                    student.save()
                    graduated_count += 1
                    
                    AuditLog.log(
                        action='STUDENT_GRADUATE',
                        user=request.user,
                        target_type='Student',
                        target_id=student.student_id,
                        target_name=f"{student.first_name} {student.last_name}",
                        description="Student graduated",
                        request=request,
                        school=school,
                    )
                    
            except Student.DoesNotExist:
                continue
        
        if promoted_count > 0:
            messages.success(request, f'{promoted_count} student(s) promoted to {target_class}.')
        if archived_count > 0:
            messages.success(request, f'{archived_count} student(s) moved to archive.')
        if graduated_count > 0:
            messages.success(request, f'{graduated_count} student(s) marked as graduated.')
        
        return redirect('core:bulk_promotion')


# ============================================================================
# TERMLY RETURN CHECKER
# ============================================================================

class TermlyReturnCheckerView(LoginRequiredMixin, TemplateView):
    """
    Class Teacher/Director of Studies view for tracking student returns each term.
    """
    template_name = 'core/dos/termly_return_checker.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = get_user_school(self.request.user)
        
        if not school:
            return ctx
        
        ctx['school'] = school
        
        # Get current term info
        current_term = school.active_term
        current_year = school.active_academic_year
        term_key = f"{current_term}_{current_year}"
        
        # Get students grouped by class
        students = Student.objects.filter(
            school=school,
            is_active=True
        ).order_by('current_class', 'last_name')
        
        students_by_class = {}
        for student in students:
            class_name = student.current_class or 'Unassigned'
            if class_name not in students_by_class:
                students_by_class[class_name] = []
            
            # Check if student needs term update
            needs_update = (
                student.last_term_checked != term_key or
                student.term_return_status == 'PENDING'
            )
            
            students_by_class[class_name].append({
                'student': student,
                'needs_update': needs_update,
                'current_status': student.term_return_status,
            })
        
        ctx['students_by_class'] = students_by_class
        ctx['current_term'] = current_term
        ctx['current_year'] = current_year
        ctx['term_key'] = term_key
        ctx['total_students'] = students.count()
        
        # Summary stats
        pending = students.filter(term_return_status='PENDING', last_term_checked=term_key).count()
        active = students.filter(term_return_status='ACTIVE', last_term_checked=term_key).count()
        not_returned = students.filter(term_return_status='NOT_RETURNED', last_term_checked=term_key).count()
        
        ctx['stats'] = {
            'pending': pending,
            'active': active,
            'not_returned': not_returned,
        }
        
        return ctx
    
    def post(self, request, *args, **kwargs):
        school = get_user_school(request.user)
        if not school:
            messages.error(request, 'No school associated with your account.')
            return redirect('core:termly_return_checker')
        
        action = request.POST.get('action')
        current_term = school.active_term
        current_year = school.active_academic_year
        term_key = f"{current_term}_{current_year}"
        
        if action == 'mark_returning':
            # Mark students as active
            student_ids = request.POST.getlist('student_ids')
            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid, school=school)
                    student.term_return_status = 'ACTIVE'
                    student.is_term_active = True
                    student.last_term_checked = term_key
                    student.save()
                    
                    AuditLog.log(
                        action='STUDENT_RETURN_CHECK',
                        user=request.user,
                        target_type='Student',
                        target_id=student.student_id,
                        target_name=f"{student.first_name} {student.last_name}",
                        description=f"Marked as returned for {current_term}/{current_year}",
                        request=request,
                        school=school,
                    )
                except Student.DoesNotExist:
                    continue
            
            messages.success(request, f'{len(student_ids)} student(s) marked as returned.')
        
        elif action == 'mark_not_returning':
            student_ids = request.POST.getlist('student_ids')
            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid, school=school)
                    student.term_return_status = 'NOT_RETURNED'
                    student.is_term_active = False
                    student.last_term_checked = term_key
                    student.save()
                    
                    AuditLog.log(
                        action='STUDENT_NOT_RETURN',
                        user=request.user,
                        target_type='Student',
                        target_id=student.student_id,
                        target_name=f"{student.first_name} {student.last_name}",
                        description=f"Marked as not returned for {current_term}/{current_year}",
                        request=request,
                        school=school,
                    )
                except Student.DoesNotExist:
                    continue
            
            messages.warning(request, f'{len(student_ids)} student(s) marked as not returned.')
        
        elif action == 'mark_all_returning':
            class_name = request.POST.get('class_name')
            students = Student.objects.filter(school=school, current_class=class_name, is_active=True)
            count = 0
            for student in students:
                student.term_return_status = 'ACTIVE'
                student.is_term_active = True
                student.last_term_checked = term_key
                student.save()
                count += 1
            
            messages.success(request, f'All {count} students in {class_name} marked as returned.')
        
        return redirect('core:termly_return_checker')


# ============================================================================
# A4 BATCH ID CARD GENERATOR
# ============================================================================

@login_required
@feature_required('ID_GENERATOR')
def batch_id_card_generator(request):
    """Generate A4 batch ID cards for students."""
    school = get_user_school(request.user)
    if not school:
        return redirect('core:dashboard')
    
    context = {
        'school': school,
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_preview':
            # Get selected students
            student_ids = request.POST.getlist('student_ids')
            include_printed = request.POST.get('include_printed') == 'on'
            
            students_qs = Student.objects.filter(
                id__in=student_ids,
                school=school,
                passport_photo__isnull=False
            ).exclude(passport_photo='')
            
            if not include_printed:
                students_qs = students_qs.filter(id_printed=False)
            
            students = list(students_qs[:40])  # Max 40 per batch (8x5 grid)
            
            context['students'] = students
            context['show_preview'] = True
            context['selected_count'] = len(students)
            context['include_printed'] = include_printed
        
        elif action == 'mark_printed':
            student_ids = request.POST.getlist('student_ids')
            from django.utils import timezone
            from core.models import UserProfile
            
            profile = get_profile(request.user)
            
            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid, school=school)
                    student.id_printed = True
                    student.id_printed_date = timezone.now()
                    student.id_printed_by = profile
                    student.save()
                    
                    AuditLog.log(
                        action='ID_CARD_PRINTED',
                        user=request.user,
                        target_type='Student',
                        target_id=student.student_id,
                        target_name=f"{student.first_name} {student.last_name}",
                        description="ID card printed",
                        request=request,
                        school=school,
                    )
                except Student.DoesNotExist:
                    continue
            
            messages.success(request, f'{len(student_ids)} student(s) marked as printed.')
            return redirect('core:batch_id_cards')
    
    # Get students for selection (only those with photos)
    students = Student.objects.filter(
        school=school,
        is_active=True,
        passport_photo__isnull=False
    ).exclude(passport_photo='').order_by('current_class', 'last_name')
    
    # Group by class
    students_by_class = {}
    for student in students:
        class_name = student.current_class or 'Unassigned'
        if class_name not in students_by_class:
            students_by_class[class_name] = []
        students_by_class[class_name].append(student)
    
    context['students_by_class'] = students_by_class
    context['total_with_photos'] = students.count()
    
    return render(request, 'core/dos/batch_id_cards.html', context)


@login_required
@feature_required('ID_GENERATOR')
def print_id_card(request, student_id):
    """Print individual student ID card."""
    school = get_user_school(request.user)
    if not school:
        return redirect('core:dashboard')
    
    try:
        student = Student.objects.get(student_id=student_id, school=school)
    except Student.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('core:batch_id_cards')
    
    context = {
        'student': student,
        'school': school,
    }
    
    return render(request, 'core/dos/id_card_single.html', context)
