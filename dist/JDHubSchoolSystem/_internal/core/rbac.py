"""
Comprehensive Role-Based Access Control (RBAC) System
Defines 8 distinct roles with specific permissions and view mappings.
"""
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

# All available roles in the system
ROLE_CHOICES = [
    ('MASTER_VENDOR', 'Master Vendor (Software Owner)'),
    ('SCHOOL_ADMIN', 'School Administrator'),
    ('HEAD_TEACHER', 'Head Teacher / Principal'),
    ('DOS', 'Director of Studies'),
    ('ACCOUNTANT', 'Accountant / Bursar'),
    ('SECRETARY', 'Secretary / Admissions'),
    ('CLASS_TEACHER', 'Class Teacher / Form Master'),
    ('SUBJECT_TEACHER', 'Subject Teacher'),
    ('PARENT', 'Parent / Guardian (Kiosk)'),
]

# Role hierarchy (higher roles inherit lower role permissions)
ROLE_HIERARCHY = {
    'MASTER_VENDOR': 100,  # Can do everything
    'SCHOOL_ADMIN': 90,    # School-level admin
    'HEAD_TEACHER': 70,   # Executive/Principal
    'DOS': 60,            # Academic management
    'ACCOUNTANT': 50,    # Finance
    'SECRETARY': 40,     # Admissions
    'CLASS_TEACHER': 30, # Class management
    'SUBJECT_TEACHER': 20, # Subject-specific
    'PARENT': 10,        # Read-only kiosk
}

# Permissions by role
ROLE_PERMISSIONS = {
    'MASTER_VENDOR': [
        # Can do everything
        '*',
    ],
    'SCHOOL_ADMIN': [
        # User management
        'user.create', 'user.edit', 'user.delete', 'user.list', 'user.reset_password',
        # Settings
        'settings.school', 'settings.academic', 'settings.backup', 'settings.restore',
        # Reports
        'reports.analytics', 'reports.academic', 'reports.finance',
        # Audit
        'audit.view', 'audit.export',
    ],
    'HEAD_TEACHER': [
        # Executive dashboard
        'dashboard.exec',
        # Reports
        'reports.academic', 'reports.summary',
        # Approval
        'approval.report_cards',
    ],
    'DOS': [
        # Academic management
        'academic.terms', 'academic.timetable', 'academic.grading',
        'academic.subjects', 'academic.exams', 'academic.promotion',
        # Reports
        'reports.academic', 'reports.exams',
    ],
    'ACCOUNTANT': [
        # Fee management
        'finance.fees', 'finance.payments', 'finance.receipts',
        'finance.reports', 'finance.reminders',
        # Messaging
        'messaging.email', 'messaging.whatsapp',
    ],
    'SECRETARY': [
        # Student management
        'student.create', 'student.edit', 'student.view', 'student.list',
        'student.admission', 'student.contact',
    ],
    'CLASS_TEACHER': [
        # Class dashboard
        'dashboard.class',
        # Class management
        'class.attendance', 'class.remarks', 'class.promotion',
        'class.termly_return',
        # Marks
        'marks.entry', 'marks.view_own_class',
    ],
    'SUBJECT_TEACHER': [
        # Subject marks only
        'marks.entry', 'marks.view_assigned',
        'attendance.subject',
    ],
    'PARENT': [
        # Kiosk read-only
        'kiosk.view_reports', 'kiosk.view_fees',
    ],
}

# Views accessible by role
ROLE_VIEW_MAPPING = {
    'MASTER_VENDOR': [
        '/master-vendor/',
        '/system/license-status/',
        '/system/settings/',
    ],
    'SCHOOL_ADMIN': [
        '/dashboard/admin/',
        '/dashboard/admin/users/',
        '/dashboard/admin/staff/',
        '/dashboard/admin/backup/',
        '/audit/',
    ],
    'HEAD_TEACHER': [
        '/head-teacher/',
        '/head-teacher/dashboard/',
        '/head-teacher/reports/',
        '/head-teacher/approve/',
    ],
    'DOS': [
        '/dos/',
        '/dos/dashboard/',
        '/dos/terms/',
        '/dos/timetable/',
        '/dos/grading/',
        '/dos/subjects/',
        '/dos/exams/',
        '/dos/reports/',
        '/dos/promotion-rules/',
        '/dos/year-end-promotion/',
    ],
    'ACCOUNTANT': [
        '/bursar/',
        '/bursar/dashboard/',
        '/bursar/fees/',
        '/bursar/payments/',
        '/bursar/receipts/',
        '/bursar/balances/',
        '/bursar/reports/',
    ],
    'SECRETARY': [
        '/secretary/',
        '/secretary/dashboard/',
        '/secretary/students/',
        '/secretary/enroll/',
    ],
    'CLASS_TEACHER': [
        '/class-teacher/',
        '/class-teacher/dashboard/',
        '/class-teacher/attendance/',
        '/class-teacher/remarks/',
        '/class-teacher/termly-return/',
        '/class-teacher/marks/',
    ],
    'SUBJECT_TEACHER': [
        '/subject-teacher/',
        '/subject-teacher/dashboard/',
        '/subject-teacher/marks/',
    ],
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_role(user):
    """Get the role for a user."""
    if not user.is_authenticated:
        return None
    
    # Superusers always get full access
    if user.is_superuser:
        return 'MASTER_VENDOR'
    
    try:
        profile = user.userprofile
        if profile and profile.role:
            return profile.role
    except Exception:
        pass
    
    return None


def get_role_level(role):
    """Get the hierarchy level for a role."""
    return ROLE_HIERARCHY.get(role, 0)


def has_role(user, allowed_roles):
    """Check if user has one of the allowed roles."""
    user_role = get_user_role(user)
    
    if not user_role:
        return False
    
    # MASTER_VENDOR can access everything
    if user_role == 'MASTER_VENDOR':
        return True
    
    # Check if user's role is in allowed roles
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    
    return user_role in allowed_roles


def has_permission(user, permission):
    """Check if user has a specific permission."""
    user_role = get_user_role(user)
    
    if not user_role:
        return False
    
    # MASTER_VENDOR has all permissions
    if user_role == 'MASTER_VENDOR':
        return True
    
    # Check role permissions
    role_perms = ROLE_PERMISSIONS.get(user_role, [])
    
    # Wildcard permission
    if '*' in role_perms:
        return True
    
    return permission in role_perms


def get_role_display_name(role):
    """Get the display name for a role."""
    for code, name in ROLE_CHOICES:
        if code == role:
            return name
    return role


# ============================================================================
# DECORATORS
# ============================================================================

def role_required(*allowed_roles, **kwargs):
    """
    Decorator to restrict view access to specific roles.
    
    Usage:
        @role_required('SCHOOL_ADMIN')
        def admin_view(request): ...
        
        @role_required('SCHOOL_ADMIN', 'HEAD_TEACHER')
        def mixed_view(request): ...
    """
    login_required_flag = kwargs.get('login_required', True)
    redirect_to = kwargs.get('redirect_to', '/accounts/login/')
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check authentication
            if login_required_flag and not request.user.is_authenticated:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                return redirect(redirect_to)
            
            # Check role
            if not has_role(request.user, allowed_roles):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': f'Access denied. Required roles: {", ".join(allowed_roles)}',
                        'code': 'ROLE_REQUIRED'
                    }, status=403)
                
                return HttpResponseForbidden(_render_access_denied_html(allowed_roles))
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required(*permissions, **kwargs):
    """
    Decorator to restrict view access to users with specific permissions.
    
    Usage:
        @permission_required('user.create', 'user.edit')
        def user_management(request): ...
    """
    login_required_flag = kwargs.get('login_required', True)
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if login_required_flag and not request.user.is_authenticated:
                return redirect('/accounts/login/')
            
            # Check all required permissions
            for perm in permissions:
                if not has_permission(request.user, perm):
                    return HttpResponseForbidden(
                        _render_permission_denied_html(permissions)
                    )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def master_vendor_only(view_func):
    """Decorator to restrict view to Master Vendor only."""
    return role_required('MASTER_VENDOR')(view_func)


def school_admin_or_above(view_func):
    """Decorator for views accessible by SCHOOL_ADMIN and above."""
    return role_required('SCHOOL_ADMIN', 'HEAD_TEACHER', 'DOS', 'ACCOUNTANT', 'SECRETARY', 'CLASS_TEACHER', 'SUBJECT_TEACHER')(view_func)


def head_teacher_or_above(view_func):
    """Decorator for views accessible by HEAD_TEACHER and above."""
    return role_required('HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR')(view_func)


def dos_or_above(view_func):
    """Decorator for views accessible by DOS and above."""
    return role_required('DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR')(view_func)


def accountant_or_above(view_func):
    """Decorator for views accessible by ACCOUNTANT and above."""
    return role_required('ACCOUNTANT', 'SCHOOL_ADMIN', 'HEAD_TEACHER', 'MASTER_VENDOR')(view_func)


def secretary_or_above(view_func):
    """Decorator for views accessible by SECRETARY and above."""
    return role_required('SECRETARY', 'CLASS_TEACHER', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR')(view_func)


def class_teacher_or_above(view_func):
    """Decorator for views accessible by CLASS_TEACHER and above."""
    return role_required('CLASS_TEACHER', 'SUBJECT_TEACHER', 'SECRETARY', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR')(view_func)


def subject_teacher_only(view_func):
    """Decorator for views accessible by SUBJECT_TEACHER only."""
    return role_required('SUBJECT_TEACHER', 'CLASS_TEACHER', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR')(view_func)


def parent_kiosk_access(view_func):
    """Decorator for parent kiosk access."""
    return role_required('PARENT', 'MASTER_VENDOR')(view_func)


# ============================================================================
# MIXINS FOR CLASS-BASED VIEWS
# ============================================================================

class RoleRequiredMixin:
    """
    Mixin to require specific roles for class-based views.
    
    Usage:
        class MyView(RoleRequiredMixin, View):
            allowed_roles = ['SCHOOL_ADMIN', 'HEAD_TEACHER']
    """
    allowed_roles = []
    login_required = True
    redirect_to = '/accounts/login/'
    
    def dispatch(self, request, *args, **kwargs):
        if self.login_required and not request.user.is_authenticated:
            return redirect(self.redirect_to)
        
        if not has_role(request.user, self.allowed_roles):
            return HttpResponseForbidden(_render_access_denied_html(self.allowed_roles))
        
        return super().dispatch(request, *args, **kwargs)


class MasterVendorMixin(RoleRequiredMixin):
    """Mixin for Master Vendor only views."""
    allowed_roles = ['MASTER_VENDOR']


class SchoolAdminMixin(RoleRequiredMixin):
    """Mixin for School Admin and above."""
    allowed_roles = ['SCHOOL_ADMIN', 'HEAD_TEACHER', 'DOS', 'ACCOUNTANT', 'SECRETARY', 'CLASS_TEACHER', 'SUBJECT_TEACHER', 'MASTER_VENDOR']


class HeadTeacherMixin(RoleRequiredMixin):
    """Mixin for Head Teacher and above."""
    allowed_roles = ['HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR']


class AccountantMixin(RoleRequiredMixin):
    """Mixin for Accountant and above."""
    allowed_roles = ['ACCOUNTANT', 'SCHOOL_ADMIN', 'HEAD_TEACHER', 'MASTER_VENDOR']


class SecretaryMixin(RoleRequiredMixin):
    """Mixin for Secretary and above."""
    allowed_roles = ['SECRETARY', 'CLASS_TEACHER', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR']


class ClassTeacherMixin(RoleRequiredMixin):
    """Mixin for Class Teacher and above."""
    allowed_roles = ['CLASS_TEACHER', 'SUBJECT_TEACHER', 'SECRETARY', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR']


class DOSMixin(RoleRequiredMixin):
    """Mixin for DOS and above."""
    allowed_roles = ['DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR']


class SecretaryMixin(RoleRequiredMixin):
    """Mixin for Secretary and above."""
    allowed_roles = ['SECRETARY', 'CLASS_TEACHER', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR']


# ============================================================================
# HTML TEMPLATES FOR ERRORS
# ============================================================================

def _render_access_denied_html(allowed_roles):
    """Render HTML for access denied page."""
    roles_display = ', '.join([get_role_display_name(r) for r in allowed_roles])
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Access Denied</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container vh-100 d-flex align-items-center justify-content-center">
            <div class="text-center">
                <div class="card shadow-lg" style="max-width: 500px;">
                    <div class="card-body p-5">
                        <i class="bi bi-shield-exclamation text-danger fs-1 mb-3 d-block"></i>
                        <h3 class="card-title mb-3">Access Denied</h3>
                        <p class="text-muted mb-4">
                            You don't have permission to access this page.<br>
                            <strong>Required: {roles_display}</strong>
                        </p>
                        <a href="/" class="btn btn-primary">
                            <i class="bi bi-house me-2"></i>Go to Dashboard
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def _render_permission_denied_html(permissions):
    """Render HTML for permission denied page."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Permission Denied</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container vh-100 d-flex align-items-center justify-content-center">
            <div class="text-center">
                <div class="card shadow-lg" style="max-width: 500px;">
                    <div class="card-body p-5">
                        <h3 class="card-title mb-3">Permission Required</h3>
                        <p class="text-muted">
                            You need additional permissions to access this feature.
                        </p>
                        <a href="/" class="btn btn-primary">Go to Dashboard</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


# ============================================================================
# CONTEXT PROCESSOR
# ============================================================================

def rbac_context(request):
    """Add RBAC info to template context."""
    if not request.user.is_authenticated:
        return {}
    
    user_role = get_user_role(request.user)
    
    return {
        'user_role': user_role,
        'user_role_display': get_role_display_name(user_role),
        'role_level': get_role_level(user_role),
        'is_master_vendor': user_role == 'MASTER_VENDOR',
        'is_school_admin': user_role in ['SCHOOL_ADMIN', 'MASTER_VENDOR'],
        'is_head_teacher': user_role in ['HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR'],
        'is_dos': user_role in ['DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR'],
        'is_accountant': user_role in ['ACCOUNTANT', 'SCHOOL_ADMIN', 'HEAD_TEACHER', 'MASTER_VENDOR'],
        'is_secretary': user_role in ['SECRETARY', 'CLASS_TEACHER', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR'],
        'is_class_teacher': user_role in ['CLASS_TEACHER', 'SUBJECT_TEACHER', 'SECRETARY', 'DOS', 'HEAD_TEACHER', 'SCHOOL_ADMIN', 'MASTER_VENDOR'],
    }


# ============================================================================
# ADMIN SETUP
# ============================================================================

def setup_role_groups():
    """
    Create Django Groups for each role.
    Call this from a management command or startup.
    """
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    
    role_groups = {}
    
    for role_code, role_name in ROLE_CHOICES:
        group, created = Group.objects.get_or_create(name=f'{role_code}')
        role_groups[role_code] = group
        
        if created:
            print(f"Created group: {role_code}")
    
    return role_groups


def assign_role_to_user(user, role):
    """Assign a role to a user."""
    from django.contrib.auth.models import Group
    
    if not user or not role:
        return False
    
    try:
        # Remove from all role groups
        for role_code in ROLE_CHOICES:
            try:
                group = Group.objects.get(name=role_code[0])
                user.groups.remove(group)
            except Group.DoesNotExist:
                pass
        
        # Add to new role group
        group = Group.objects.get(name=role)
        user.groups.add(group)
        
        # Update profile role
        try:
            profile = user.userprofile
            profile.role = role
            profile.save()
        except Exception:
            pass
        
        return True
    except Exception as e:
        print(f"Error assigning role: {e}")
        return False


if __name__ == '__main__':
    setup_role_groups()
    print("Role groups created successfully!")
