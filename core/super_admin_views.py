"""Super Admin control panel — full system configuration for Jordan / SUPER_ADMIN."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, FileResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
from django.views.generic import TemplateView

from .forms import (
    SuperAdminSchoolForm, SuperAdminFeatureForm, SuperAdminTerminologyForm,
    SuperAdminGradingForm, SuperAdminPeriodForm, ClassPromotionRuleForm,
    StudentTermRecordForm, StaffPasswordResetForm, SuperAdminBackupForm,
)
from .models import (
    SchoolConfiguration, UserProfile, SchoolTermArchive, ClassPromotionRule,
    Student, StudentTermRecord, SchoolClass, MarkEntry,
)
from .backup_utils import (
    create_backup_zip, create_schoolhub_backup, save_backup_to_disk, save_schoolhub_to_disk,
    restore_backup_zip, get_local_network_url, should_run_auto_backup, reset_system_factory,
    get_lan_ip, cloud_outbox_dir,
)
from .school_config_utils import (
    close_current_term, deactivate_user, activate_user, reset_user_password,
    is_term_locked,
)
from .report_services import get_or_init_term_record
from .views import RoleRequiredMixin, get_profile, get_user_school, render_pdf_response, pdf_base_context


class SuperAdminOnlyMixin(RoleRequiredMixin):
    allowed_roles = ['SUPER_ADMIN']


def _control_redirect(tab=None):
    url = reverse('core:super_admin_control')
    if tab:
        return redirect(f'{url}?tab={tab}')
    return redirect(url)


class SuperAdminControlView(SuperAdminOnlyMixin, TemplateView):
    template_name = 'core/admin/control_panel.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        if not school:
            return ctx

        ctx['school_form'] = SuperAdminSchoolForm(instance=school)
        ctx['feature_form'] = SuperAdminFeatureForm(instance=school)
        ctx['terminology_form'] = SuperAdminTerminologyForm(instance=school)
        ctx['grading_form'] = SuperAdminGradingForm(instance=school)
        ctx['period_form'] = SuperAdminPeriodForm(instance=school)
        ctx['promotion_rules'] = ClassPromotionRule.objects.filter(school=school)
        ctx['rule_form'] = ClassPromotionRuleForm()
        ctx['term_archives'] = SchoolTermArchive.objects.filter(school=school)[:20]
        ctx['staff_users'] = UserProfile.objects.filter(school=school).select_related('user')
        ctx['classes'] = SchoolClass.objects.filter(school=school)
        ctx['current_term_locked'] = school.current_term_locked or is_term_locked(school)
        ctx['password_form'] = StaffPasswordResetForm()
        ctx['backup_form'] = SuperAdminBackupForm(instance=school)
        ctx['network_url'] = get_local_network_url(self.request)
        ctx['lan_ip'] = get_lan_ip()
        ctx['qr_url'] = ctx['network_url']
        ctx['backup_due'] = should_run_auto_backup(school)
        ctx['cloud_outbox_count'] = len(list(cloud_outbox_dir().glob('*.schoolhub')))
        ctx['tab'] = self.request.GET.get('tab', 'system')
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        action = request.POST.get('action')

        if action == 'save_backup_settings':
            form = SuperAdminBackupForm(request.POST, instance=school)
            if form.is_valid():
                form.save()
                messages.success(request, 'Backup settings saved.')
            return _control_redirect('backup')

        if action == 'export_backup_disk':
            path = save_schoolhub_to_disk(school)
            school.backup_last_export_at = timezone.now()
            school.save(update_fields=['backup_last_export_at'])
            messages.success(request, f'Encrypted backup saved to {path}')
            return _control_redirect('backup')

        if action == 'import_backup':
            f = request.FILES.get('backup_file')
            if f:
                try:
                    result = restore_backup_zip(f)
                    msg = 'System backup loaded successfully. Data is live — refresh any open pages.'
                    if isinstance(result, dict) and result.get('rollback_dir'):
                        msg += f' Rollback snapshot: {result["rollback_dir"]}'
                    messages.success(request, msg)
                except Exception as exc:
                    messages.error(request, str(exc))
            else:
                messages.error(request, 'Select a .schoolhub or .zip backup file.')
            return _control_redirect('backup')

        if action == 'reset_system':
            confirm = request.POST.get('reset_confirm', '').strip().upper()
            if confirm != 'RESET':
                messages.error(request, 'Type RESET in the confirmation box to wipe the system.')
                return _control_redirect('backup')
            reset_system_factory(request.user)
            messages.success(request, 'System reset complete. All data cleared except your Jordan account.')
            return _control_redirect('system')

        if action == 'save_school_status':
            form = SuperAdminSchoolForm(request.POST, instance=school)
            if form.is_valid():
                form.save()
                messages.success(request, 'School status updated.')
            else:
                messages.error(request, 'Could not save school status.')
            return redirect('core:super_admin_control')

        if action == 'save_features':
            form = SuperAdminFeatureForm(request.POST, instance=school)
            if form.is_valid():
                form.save()
                messages.success(request, 'Feature settings saved.')
            return redirect('core:super_admin_control')

        if action == 'save_terminology':
            form = SuperAdminTerminologyForm(request.POST, instance=school)
            if form.is_valid():
                form.save()
                messages.success(request, 'Institution labels saved.')
            return redirect('core:super_admin_control')

        if action == 'save_grading':
            form = SuperAdminGradingForm(request.POST, instance=school)
            if form.is_valid():
                form.save()
                messages.success(request, 'Grading system updated.')
            return redirect('core:super_admin_control')

        if action == 'save_periods':
            form = SuperAdminPeriodForm(request.POST, instance=school)
            if form.is_valid():
                obj = form.save(commit=False)
                if obj.academic_period_type == SchoolConfiguration.PERIOD_SEMESTERS:
                    if obj.periods_per_year not in (1, 2, 3):
                        obj.periods_per_year = 2
                elif obj.periods_per_year not in (1, 2, 3, 4):
                    obj.periods_per_year = 3
                obj.save()
                messages.success(request, 'Academic period settings saved.')
            return redirect('core:super_admin_control')

        if action == 'close_term':
            notes = request.POST.get('close_notes', '')
            carry = request.POST.get('carry_fees') == 'on'
            advance_term = request.POST.get('advance_term', '').strip()
            advance_year = request.POST.get('advance_year', '').strip()
            old_term, old_year = school.active_term, school.active_academic_year
            close_current_term(
                school, profile, notes=notes, carry_fees=carry,
                advance_to_term=advance_term or None,
                advance_to_year=advance_year or None,
            )
            school.refresh_from_db()
            messages.success(
                request,
                f'Term {old_term}/{old_year} closed and locked. '
                f'Active period is now {school.active_term}/{school.active_academic_year}. '
                'DOS and Head Teacher can view archived reports.',
            )
            return redirect('core:super_admin_control')

        if action == 'unlock_current_term':
            school.current_term_locked = False
            school.save(update_fields=['current_term_locked'])
            messages.success(request, 'Current term unlocked for editing (super admin override).')
            return redirect('core:super_admin_control')

        if action == 'save_promotion_rule':
            rule_id = request.POST.get('rule_id')
            if rule_id:
                rule = get_object_or_404(ClassPromotionRule, pk=rule_id, school=school)
                form = ClassPromotionRuleForm(request.POST, instance=rule)
            else:
                form = ClassPromotionRuleForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.school = school
                obj.save()
                messages.success(request, 'Promotion rule saved.')
            return redirect('core:super_admin_control')

        if action == 'delete_promotion_rule':
            rule = ClassPromotionRule.objects.filter(pk=request.POST.get('rule_id'), school=school).first()
            if rule:
                rule.delete()
                messages.success(request, 'Promotion rule removed.')
            return redirect('core:super_admin_control')

        if action == 'toggle_user':
            target = UserProfile.objects.filter(pk=request.POST.get('user_id'), school=school).first()
            if target:
                if target.is_active:
                    ok, msg = deactivate_user(target, profile)
                else:
                    ok, msg = activate_user(target)
                messages.success(request, msg) if ok else messages.error(request, msg)
            return redirect('core:super_admin_control')

        if action == 'delete_user':
            target = UserProfile.objects.filter(pk=request.POST.get('user_id'), school=school).select_related('user').first()
            if target and target.user_id != request.user.id:
                username = target.user.username
                target.user.delete()
                messages.success(request, f'User "{username}" removed.')
            elif target:
                messages.error(request, 'You cannot delete your own account.')
            return redirect('core:super_admin_control')

        if action == 'reset_password':
            target = UserProfile.objects.filter(pk=request.POST.get('user_id'), school=school).first()
            form = StaffPasswordResetForm(request.POST)
            if target and form.is_valid():
                reset_user_password(target, form.cleaned_data['new_password'])
                messages.success(request, f'Password reset for {target.user.username}.')
            else:
                messages.error(request, 'Invalid password.')
            return redirect('core:super_admin_control')

        if action == 'save_remarks':
            student = get_object_or_404(Student, pk=request.POST.get('student_id'), school=school)
            term = request.POST.get('term') or school.active_term
            year = request.POST.get('year') or school.active_academic_year
            record, _ = get_or_init_term_record(student, term, year)
            form = StudentTermRecordForm(request.POST, instance=record)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.updated_by = profile
                obj.save()
                messages.success(request, f'Remarks saved for {student.first_name} {student.last_name}.')
            return redirect('core:super_admin_control')

        return redirect('core:super_admin_control')


class ArchivedTermReportsView(RoleRequiredMixin, TemplateView):
    """Closed-term reports — DOS and Head Teacher only."""
    template_name = 'core/admin/archived_reports.html'
    allowed_roles = ['DOS', 'HEAD_TEACHER', 'SUPER_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        if not school:
            return ctx

        archives = SchoolTermArchive.objects.filter(
            school=school, records_locked=True,
        ).order_by('-closed_at')
        ctx['archives'] = archives

        term = self.request.GET.get('term')
        year = self.request.GET.get('year')
        if term and year:
            ctx['selected_term'] = term
            ctx['selected_year'] = year
            rows = []
            for student in Student.objects.filter(school=school, is_active=True).order_by('current_class', 'last_name'):
                record = StudentTermRecord.objects.filter(
                    student=student, term=term, academic_year=year,
                ).first()
                mark_count = MarkEntry.objects.filter(
                    student=student, grading_term=term, academic_year=year,
                ).count()
                rows.append({
                    'student': student, 'record': record, 'mark_count': mark_count,
                })
            ctx['student_rows'] = rows
            ctx['archive'] = archives.filter(term=term, academic_year=year).first()
        return ctx


@login_required
def export_system_backup(request):
    profile = get_profile(request.user)
    if not profile or profile.role != 'SUPER_ADMIN':
        raise Http404()
    buffer, filename = create_backup_zip()
    school = get_user_school(profile)
    if school:
        school.backup_last_export_at = timezone.now()
        school.save(update_fields=['backup_last_export_at'])
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def export_schoolhub_backup(request):
    profile = get_profile(request.user)
    if not profile or profile.role != 'SUPER_ADMIN':
        raise Http404()
    school = get_user_school(profile)
    buffer, filename = create_schoolhub_backup(school)
    if school:
        school.backup_last_export_at = timezone.now()
        school.save(update_fields=['backup_last_export_at'])
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def student_id_cards_pdf(request):
    profile = get_profile(request.user)
    if not profile or profile.role != 'SUPER_ADMIN':
        raise Http404()
    school = get_user_school(profile)
    class_name = request.GET.get('class', '')
    limit = request.GET.get('limit', 'all')
    per_page = int(request.GET.get('per_page', '8'))

    students = Student.objects.filter(school=school, is_active=True)
    if class_name:
        students = students.filter(current_class=class_name)
    students = students.order_by('last_name', 'first_name')
    if limit != 'all':
        try:
            students = students[:int(limit)]
        except ValueError:
            pass

    cards = list(students)
    pages = []
    for i in range(0, len(cards), per_page):
        pages.append(cards[i:i + per_page])

    cols = 2
    if per_page <= 4:
        rows = 2
    elif per_page <= 6:
        rows = 3
    elif per_page <= 8:
        rows = 4
    else:
        rows = 5

    html = render_to_string('core/pdf/student_id_cards.html', {
        **pdf_base_context(school),
        'pages': pages,
        'per_page': per_page,
        'cols': cols,
        'rows': rows,
        'class_name': class_name or 'All Classes',
    })
    return render_pdf_response(html, f'student_ids_{class_name or "all"}.pdf')


def pwa_manifest(request):
    from django.templatetags.static import static
    school = SchoolConfiguration.get_school()
    name = school.network_app_name if school else 'Jordan Hub School System'
    icon = static('core/icon-192.png')
    return HttpResponse(
        f'''{{
  "name": "{name}",
  "short_name": "Jordan Hub",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "icons": [
    {{"src": "{icon}", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"}},
    {{"src": "{static('core/icon-512.png')}", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}},
    {{"src": "{static('core/favicon.ico')}", "sizes": "64x64", "type": "image/x-icon"}}
  ]
}}''',
        content_type='application/manifest+json',
    )


def pwa_service_worker(request):
    from django.contrib.staticfiles.storage import staticfiles_storage
    try:
        sw_path = staticfiles_storage.path('core/sw.js')
        with open(sw_path, encoding='utf-8') as f:
            content = f.read()
    except (OSError, ValueError):
        from django.template.loader import render_to_string
        content = render_to_string('core/sw.js', request=request)
    return HttpResponse(content, content_type='application/javascript')
