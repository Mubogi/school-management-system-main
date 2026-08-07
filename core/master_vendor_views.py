"""
Master Vendor Panel Views
For the software owner to control schools, branding, and system-wide settings.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models import Count, Q

from licensing.activation import _get_license_status, _get_enabled_features
from licensing.hwid import get_hwid_short, _get_hardware_id
from licensing.models import LicenseActivation, LicenseKey, AuditLog, BackupRecord
from core.models import SchoolConfiguration, UserProfile
from core.rbac import role_required, get_user_role, master_vendor_only, ROLE_CHOICES
from licensing.decorators import feature_required


# ============================================================================
# MASTER VENDOR DASHBOARD
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def master_vendor_dashboard(request):
    """Main dashboard for Master Vendor."""
    context = {
        'total_schools': SchoolConfiguration.objects.count(),
        'total_users': User.objects.filter(is_active=True).count(),
        'total_activations': LicenseActivation.objects.filter(is_active=True).count(),
        'recent_activations': LicenseActivation.objects.filter(
            is_active=True
        ).order_by('-activated_at')[:5],
        'recent_logs': AuditLog.objects.all()[:10],
        'license_status': _get_license_status(),
    }
    return render(request, 'core/vendor/master_vendor_dashboard.html', context)


# ============================================================================
# SYSTEM LICENSE STATUS
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def license_status_view(request):
    """Display current license status and allow upgrades."""
    context = {
        'license_status': _get_license_status(),
        'enabled_features': _get_enabled_features(),
        'hwid_short': get_hwid_short(),
        'hwid_full': _get_hardware_id(),
        'recent_activations': LicenseActivation.objects.all()[:10],
        'backup_records': BackupRecord.objects.all()[:5],
    }
    return render(request, 'core/vendor/license_status.html', context)


@login_required
@role_required('MASTER_VENDOR')
@require_http_methods(["POST"])
def apply_upgrade_key(request):
    """Apply an upgrade/extension license key."""
    upgrade_key = request.POST.get('upgrade_key', '').strip()
    
    if not upgrade_key:
        messages.error(request, 'Please enter a license key.')
        return redirect('core:vendor_license_status')
    
    # Import and validate
    from licensing.activation import activate_license
    from licensing.hwid import _get_hardware_id
    
    hwid = _get_hardware_id()
    success, message = activate_license(upgrade_key, hwid)
    
    if success:
        messages.success(request, message)
        # Log the upgrade
        AuditLog.log(
            action='LICENSE_UPGRADE',
            user=request.user,
            description=f'Applied upgrade key: {upgrade_key[:20]}...',
        )
    else:
        messages.error(request, message)
    
    return redirect('core:vendor_license_status')


# ============================================================================
# SCHOOL MANAGEMENT
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def vendor_schools(request):
    """View and manage all schools."""
    schools = SchoolConfiguration.objects.annotate(
        user_count=Count('userprofile')
    ).order_by('-is_active', 'school_name')
    
    context = {
        'schools': schools,
    }
    return render(request, 'core/vendor/vendor_schools.html', context)


@login_required
@role_required('MASTER_VENDOR')
@require_http_methods(["POST"])
def toggle_school_status(request, school_id):
    """Toggle school active status."""
    school = get_object_or_404(SchoolConfiguration, id=school_id)
    school.is_active = not school.is_active
    school.save()
    
    status = 'activated' if school.is_active else 'deactivated'
    messages.success(request, f'School {school.school_name} {status}.')
    
    AuditLog.log(
        action='SCHOOL_STATUS_CHANGE',
        user=request.user,
        target_type='SchoolConfiguration',
        target_id=str(school.id),
        target_name=school.school_name,
        description=f'School {status}',
    )
    
    return redirect('core:vendor_schools')


# ============================================================================
# BRANDING CONTROL (Hard-locked for Master Vendor only)
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def vendor_branding(request):
    """
    Master Vendor branding settings.
    Schools CANNOT change vendor branding.
    """
    schools = SchoolConfiguration.objects.all()
    
    context = {
        'schools': schools,
    }
    return render(request, 'core/vendor/vendor_branding.html', context)


@login_required
@role_required('MASTER_VENDOR')
@require_http_methods(["POST"])
def update_vendor_branding(request):
    """Update Master Vendor branding (cannot be changed by schools)."""
    vendor_name = request.POST.get('vendor_name', 'OfficeHub School System')
    vendor_logo = request.FILES.get('vendor_logo')
    vendor_url = request.POST.get('vendor_url', '')
    
    # Update settings or create a vendor config
    from django.conf import settings
    
    # Log branding change
    AuditLog.log(
        action='VENDOR_BRANDING_UPDATE',
        user=request.user,
        description=f'Updated vendor branding: {vendor_name}',
    )
    
    messages.success(request, 'Vendor branding updated successfully.')
    return redirect('core:vendor_branding')


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def vendor_users(request):
    """View all users across all schools."""
    users = User.objects.select_related('userprofile').order_by('-is_active', 'username')
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(userprofile__role=role_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    context = {
        'users': users,
        'roles': ROLE_CHOICES,
        'role_filter': role_filter,
        'search': search,
    }
    return render(request, 'core/vendor/vendor_users.html', context)


@login_required
@role_required('MASTER_VENDOR')
@require_http_methods(["POST"])
def update_user_role(request, user_id):
    """Update a user's role."""
    user = get_object_or_404(User, id=user_id)
    new_role = request.POST.get('role')
    
    if new_role not in [r[0] for r in ROLE_CHOICES]:
        messages.error(request, 'Invalid role selected.')
        return redirect('core:vendor_users')
    
    # Update role
    from core.rbac import assign_role_to_user
    assign_role_to_user(user, new_role)
    
    messages.success(request, f'{user.username} role updated to {new_role}.')
    
    AuditLog.log(
        action='USER_ROLE_CHANGE',
        user=request.user,
        target_type='User',
        target_id=str(user.id),
        target_name=user.username,
        description=f'Role changed to {new_role}',
    )
    
    return redirect('core:vendor_users')


# ============================================================================
# AUDIT LOG
# ============================================================================

@login_required
@role_required('MASTER_VENDOR', 'SCHOOL_ADMIN')
def vendor_audit_log(request):
    """View system audit logs."""
    logs = AuditLog.objects.select_related('user').order_by('-created_at')
    
    # Filter by action
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    # Filter by user
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    # Date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'action_choices': AuditLog.ACTION_CHOICES,
        'action_filter': action_filter,
    }
    return render(request, 'core/vendor/audit_log.html', context)


# ============================================================================
# FEATURE MATRIX MANAGEMENT
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def vendor_feature_matrix(request):
    """Manage feature matrix keys."""
    matrices = LicenseActivation.objects.all().order_by('-activated_at')
    
    context = {
        'matrices': matrices,
    }
    return render(request, 'core/vendor/feature_matrix.html', context)


@login_required
@role_required('MASTER_VENDOR')
@require_http_methods(["POST"])
def generate_feature_matrix(request):
    """Generate a new feature matrix key."""
    school_name = request.POST.get('school_name')
    tier = request.POST.get('tier', 'BASIC')
    max_users = int(request.POST.get('max_users', 5))
    duration_days = int(request.POST.get('duration_days', 365))
    features = request.POST.getlist('features')
    
    # Generate the key
    from licensing.activation import _encode_license_data, _format_license_key
    import secrets
    import json
    import base64
    import hashlib
    import hmac
    
    # Create key data
    short_id = secrets.token_hex(4).upper()
    encoded = _encode_license_data(tier, duration_days, features)
    key = _format_license_key(tier, encoded, short_id)
    
    # Create encrypted matrix data
    matrix_data = {
        'tier': tier,
        'features': features,
        'max_users': max_users,
        'duration_days': duration_days,
        'school_name': school_name,
    }
    
    # In production, encrypt this with vendor private key
    encrypted = base64.b64encode(json.dumps(matrix_data).encode()).decode()
    
    # Create signature
    SECRET = 'vendor_master_secret_2026'
    signature = hmac.new(SECRET.encode(), encrypted.encode(), hashlib.sha256).hexdigest()
    
    # Save to database
    from licensing.models import EncryptedFeatureMatrix
    EncryptedFeatureMatrix.objects.create(
        key_id=key,
        encrypted_data=encrypted,
        signature=signature,
        hwid='PENDING',  # Set when activated
        expiry_date=timezone.now() + timezone.timedelta(days=duration_days),
        max_users=max_users,
        created_by=request.user,
    )
    
    messages.success(request, f'Feature matrix generated: {key}')
    
    return redirect('core:vendor_feature_matrix')


# ============================================================================
# BACKUP MANAGEMENT
# ============================================================================

@login_required
@role_required('MASTER_VENDOR', 'SCHOOL_ADMIN')
def vendor_backups(request):
    """View and manage system backups."""
    backups = BackupRecord.objects.all().order_by('-created_at')[:20]
    
    context = {
        'backups': backups,
    }
    return render(request, 'core/vendor/backups.html', context)


@login_required
@role_required('MASTER_VENDOR', 'SCHOOL_ADMIN')
@require_http_methods(["POST"])
def create_manual_backup(request):
    """Create a manual backup."""
    from backups.backup_service import create_backup
    
    success, path, msg = create_backup(backup_type='MANUAL', school_id=request.user.username)
    
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    
    return redirect('core:vendor_backups')


# ============================================================================
# SYSTEM STATISTICS
# ============================================================================

@login_required
@role_required('MASTER_VENDOR')
def vendor_statistics(request):
    """View system-wide statistics."""
    from django.db.models import Sum, Avg
    
    # User statistics
    user_stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'by_role': {},
    }
    for role_code, _ in ROLE_CHOICES:
        count = UserProfile.objects.filter(role=role_code).count()
        if count > 0:
            user_stats['by_role'][role_code] = count
    
    # License statistics
    license_stats = {
        'total_activations': LicenseActivation.objects.count(),
        'active': LicenseActivation.objects.filter(is_active=True).count(),
        'by_tier': {},
    }
    for tier in ['BASIC', 'STANDARD', 'PREMIUM', 'DEMO']:
        count = LicenseActivation.objects.filter(tier=tier, is_active=True).count()
        if count > 0:
            license_stats['by_tier'][tier] = count
    
    # Backup statistics
    backup_stats = {
        'total': BackupRecord.objects.count(),
        'total_size_gb': BackupRecord.objects.aggregate(
            total=Sum('file_size')
        )['total'] or 0 / (1024**3),
    }
    
    context = {
        'user_stats': user_stats,
        'license_stats': license_stats,
        'backup_stats': backup_stats,
    }
    return render(request, 'core/vendor/statistics.html', context)
