"""
Licensing Views
Handles activation, license management, and status display.
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .activation import (
    _validate_license_key as validate_license_key,
    _get_license_status as get_license_status,
    activate_license,
    deactivate_license,
    _is_activated as is_activated,
    _get_enabled_features as get_enabled_features,
)
from .hwid import _get_hardware_id as get_hardware_id, get_hwid_short
from .models import LicenseActivation, LicenseLog


def activation_view(request):
    """Main activation page - shows current status and activation form."""
    status = get_license_status()
    hwid = get_hardware_id()
    hwid_short = get_hwid_short()
    
    context = {
        'status': status,
        'hwid': hwid,
        'hwid_short': hwid_short,
        'is_activated': status['is_activated'],
        'features': get_enabled_features(),
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'activate':
            key = request.POST.get('license_key', '').strip()
            
            if not key:
                messages.error(request, 'Please enter a license key.')
                return render(request, 'licensing/activate.html', context)
            
            success, message = activate_license(key, hwid)
            
            if success:
                # Log successful activation
                LicenseLog.objects.create(
                    action='ACTIVATED',
                    license_key=key,
                    hwid=hwid,
                    details=f"Activated on machine {hwid_short}",
                    ip_address=get_client_ip(request),
                )
                messages.success(request, message)
                return redirect('/')
            else:
                LicenseLog.objects.create(
                    action='FAILED',
                    license_key=key,
                    hwid=hwid,
                    details=message,
                    ip_address=get_client_ip(request),
                )
                messages.error(request, message)
                return render(request, 'licensing/activate.html', context)
        
        elif action == 'deactivate':
            if deactivate_license():
                LicenseLog.objects.create(
                    action='DEACTIVATED',
                    hwid=hwid,
                    details='License deactivated',
                    ip_address=get_client_ip(request),
                )
                messages.success(request, 'License deactivated successfully.')
            else:
                messages.error(request, 'Failed to deactivate license.')
            
            return redirect('/activate/')
    
    return render(request, 'licensing/activate.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def license_management(request):
    """Super admin license management view."""
    status = get_license_status()
    hwid = get_hardware_id()
    activations = LicenseActivation.objects.all()[:10]
    logs = LicenseLog.objects.all()[:20]
    
    context = {
        'status': status,
        'hwid': hwid,
        'activations': activations,
        'logs': logs,
    }
    
    return render(request, 'licensing/management.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def force_logout_session(request):
    """Force logout a specific user session."""
    session_key = request.POST.get('session_key')
    
    if session_key:
        from django.contrib.sessions.backends.db import SessionStore
        try:
            session = SessionStore(session_key=session_key)
            session.flush()
            messages.success(request, 'User session terminated successfully.')
        except Exception as e:
            messages.error(request, f'Failed to terminate session: {str(e)}')
    
    return redirect('licensing:session_management')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def session_management(request):
    """View and manage active user sessions."""
    from django.contrib.sessions.models import Session
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    active_sessions = []
    
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
                active_sessions.append({
                    'session_key': session.session_key,
                    'user': user,
                    'last_login': user.last_login,
                    'is_online': True,
                })
            except User.DoesNotExist:
                pass
    
    context = {
        'sessions': active_sessions,
        'total_sessions': len(active_sessions),
    }
    
    return render(request, 'licensing/sessions.html', context)


def api_check_license(request):
    """API endpoint to check license status."""
    status = get_license_status()
    return JsonResponse({
        'activated': status['is_activated'],
        'tier': status['tier'],
        'features': status['features'],
        'expires_at': status['expires_at'].isoformat() if status['expires_at'] else None,
    })


def api_validate_key(request):
    """API endpoint to validate a license key without activating."""
    key = request.GET.get('key', '')
    hwid = get_hardware_id()
    
    is_valid, message, license_info = validate_license_key(key, hwid)
    
    return JsonResponse({
        'valid': is_valid,
        'message': message,
        'tier': license_info.tier,
        'features': license_info.features,
    })


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Import timezone for session check
from django.utils import timezone
