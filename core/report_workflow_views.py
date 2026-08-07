"""Views for publish/lock, remarks, notifications, and promotion."""
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.http import Http404

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
    RoleRequiredMixin, get_profile, LoginRequiredMixin, get_user_school,
)


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
