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
    
    # Get all possible URLs for the manifest
    base_url = request.build_absolute_uri('/')[:-1]
    
    return HttpResponse(
        f'''{{
  "name": "{name}",
  "short_name": "Jordan Hub",
  "description": "Complete school management solution",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "lang": "en-US",
  "categories": ["education", "business"],
  "icons": [
    {{"src": "{icon}", "sizes": "192x192", "type": "image/png", "purpose": "any"}},
    {{"src": "{static('core/icon-512.png')}", "sizes": "512x512", "type": "image/png", "purpose": "any"}},
    {{"src": "{static('core/icon-maskable.png')}", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}},
    {{"src": "{static('core/favicon.ico')}", "sizes": "64x64", "type": "image/x-icon"}}
  ],
  "screenshots": [],
  "shortcuts": [
    {{"name": "Dashboard", "url": "/", "description": "Go to main dashboard"}},
    {{"name": "Students", "url": "/search/students/", "description": "Search students"}}
  ],
  "handle_links": "preferred",
  "launch_handler": {{"client_mode": "navigate-existing"}}
}}''',
        content_type='application/manifest+json',
    )


def pwa_service_worker(request):
    from django.contrib.staticfiles.storage import staticfiles_storage
    sw_path = staticfiles_storage.path('core/sw.js')
    with open(sw_path, encoding='utf-8') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/javascript')


# ============================================================================
# DATABASE MANAGEMENT & SESSION CONTROL
# ============================================================================

class DatabaseManagementView(SuperAdminOnlyMixin, TemplateView):
    """Super Admin database management page."""
    template_name = 'core/admin/database_management.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        
        # Get database info
        import os
        from datetime import datetime
        from django.conf import settings
        
        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
            ctx['db_size'] = db_size
            ctx['db_size_mb'] = round(db_size / (1024 * 1024), 2)
            mtime = os.path.getmtime(db_path)
            ctx['db_modified'] = datetime.fromtimestamp(mtime)
        else:
            ctx['db_size'] = 0
            ctx['db_size_mb'] = 0
            ctx['db_modified'] = None
        
        ctx['db_path'] = db_path
        
        # Backup history
        from .models import SchoolConfiguration
        from licensing.models import AuditLog
        
        ctx['backup_logs'] = AuditLog.objects.filter(
            action='BACKUP_CREATE'
        ).select_related('user')[:10]
        
        return ctx


def create_instant_backup(request):
    """Create an instant database backup."""
    import shutil
    import os
    from django.conf import settings
    from django.utils import timezone
    
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    
    try:
        db_path = settings.DATABASES['default']['NAME']
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backups directory
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy database
        backup_name = f'db_backup_{timestamp}.sqlite3'
        backup_path = os.path.join(backup_dir, backup_name)
        shutil.copy2(db_path, backup_path)
        
        # Also create a backup_info.json
        import json
        info = {
            'timestamp': timestamp,
            'created_by': request.user.username,
            'original_size': os.path.getsize(db_path),
            'backup_path': backup_path,
        }
        info_path = os.path.join(backup_dir, f'backup_info_{timestamp}.json')
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
        
        # Log the action
        from licensing.models import AuditLog
        AuditLog.log(
            action='BACKUP_CREATE',
            user=request.user,
            target_type='Database',
            target_id=backup_name,
            description=f'Created backup: {backup_name}',
            request=request,
        )
        
        messages.success(request, f'Backup created successfully: {backup_name}')
        
    except Exception as e:
        messages.error(request, f'Backup failed: {str(e)}')
    
    return redirect('core:database_management')


def download_backup(request, backup_name):
    """Download a specific backup file."""
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    
    import os
    from django.conf import settings
    
    backup_path = os.path.join(settings.BASE_DIR, 'backups', backup_name)
    
    if not os.path.exists(backup_path):
        raise Http404('Backup not found')
    
    response = FileResponse(
        open(backup_path, 'rb'),
        as_attachment=True,
        filename=backup_name
    )
    return response


class SessionManagementView(SuperAdminOnlyMixin, TemplateView):
    """Super Admin session management page."""
    template_name = 'core/admin/session_management.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        
        # Get active sessions
        from django.contrib.sessions.models import Session
        from django.contrib.auth.models import User
        
        active_sessions = []
        sessions = Session.objects.filter(
            expire_date__gte=timezone.now()
        ).order_by('-expire_date')
        
        for session in sessions:
            session_data = session.get_decoded()
            user_id = session_data.get('_auth_user_id')
            
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    user_profile = getattr(user, 'userprofile', None)
                    
                    active_sessions.append({
                        'session_key': session.session_key,
                        'user': user,
                        'username': user.username,
                        'role': user_profile.role if user_profile else 'Unknown',
                        'last_login': user.last_login,
                        'ip_address': session_data.get('ip_address', 'N/A'),
                        'expires': session.expire_date,
                    })
                except User.DoesNotExist:
                    continue
        
        ctx['active_sessions'] = active_sessions
        ctx['session_count'] = len(active_sessions)
        
        # Current session info
        if self.request.session.session_key:
            ctx['current_session_key'] = self.request.session.session_key
        
        return ctx


def terminate_session(request, session_key):
    """Terminate a specific session."""
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    
    from django.contrib.sessions.models import Session
    from django.contrib.auth.models import User
    from licensing.models import AuditLog
    
    try:
        session = Session.objects.get(session_key=session_key)
        session_data = session.get_decoded()
        user_id = session_data.get('_auth_user_id')
        
        # Don't allow terminating own session
        if request.session.session_key == session_key:
            messages.error(request, 'Cannot terminate your own session.')
            return redirect('core:session_management')
        
        # Get username for logging
        username = 'Unknown'
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                username = user.username
            except User.DoesNotExist:
                pass
        
        # Log the action
        AuditLog.log(
            action='SESSION_TERMINATE',
            user=request.user,
            target_type='Session',
            target_id=session_key,
            description=f'Terminated session for user: {username}',
            request=request,
        )
        
        # Delete the session
        session.delete()
        
        messages.success(request, f'Session for {username} has been terminated.')
        
    except Session.DoesNotExist:
        messages.error(request, 'Session not found.')
    
    return redirect('core:session_management')


def terminate_all_sessions(request):
    """Terminate all sessions except the current one."""
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    
    from django.contrib.sessions.models import Session
    from licensing.models import AuditLog
    
    current_key = request.session.session_key
    
    # Delete all sessions except current
    deleted_count = Session.objects.exclude(
        session_key=current_key
    ).filter(
        expire_date__gte=timezone.now()
    ).delete()[0]
    
    # Log the action
    AuditLog.log(
        action='SESSION_TERMINATE',
        user=request.user,
        description=f'Terminated {deleted_count} sessions',
        request=request,
    )
    
    messages.success(request, f'{deleted_count} session(s) terminated.')
    return redirect('core:session_management')


class AuditLogView(SuperAdminOnlyMixin, TemplateView):
    """View audit logs."""
    template_name = 'core/admin/audit_log.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        
        from licensing.models import AuditLog
        from django.db.models import Q
        
        # Filter by action if provided
        action_filter = self.request.GET.get('action')
        user_filter = self.request.GET.get('user')
        
        logs = AuditLog.objects.select_related('user').order_by('-created_at')
        
        if action_filter:
            logs = logs.filter(action=action_filter)
        
        if user_filter:
            logs = logs.filter(username__icontains=user_filter)
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(logs, 50)
        page = self.request.GET.get('page', 1)
        ctx['logs'] = paginator.get_page(page)
        
        # Get unique actions for filter dropdown
        ctx['action_choices'] = AuditLog.ACTION_CHOICES
        
        return ctx
