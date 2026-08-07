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


# ============================================================================
# FEATURE ACTIVATION VIEWS
# ============================================================================

@require_http_methods(["GET", "POST"])
def feature_activation_view(request):
    """
    View for activating features using 8-digit keys.
    Accessible by all authenticated users.
    """
    from .models import FeatureActivationKey, FEATURE_CHOICES
    from .activation import enable_feature_temporary
    
    status = get_license_status()
    current_features = get_enabled_features()
    
    context = {
        'status': status,
        'features': FEATURE_CHOICES,
        'current_features': current_features,
        'feature_status': get_feature_status(),
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'activate_feature':
            key = request.POST.get('activation_key', '').strip()
            
            if not key:
                messages.error(request, 'Please enter an activation key.')
                return render(request, 'licensing/activate_feature.html', context)
            
            # Validate the key
            try:
                feature_key = FeatureActivationKey.objects.get(key=key)
                
                if not feature_key.is_valid():
                    messages.error(request, 'This activation key has expired or already been used.')
                    return render(request, 'licensing/activate_feature.html', context)
                
                # Use the key
                feature_key.is_used = True
                feature_key.used_by = str(request.user) if request.user.is_authenticated else 'Anonymous'
                feature_key.used_at = timezone.now()
                feature_key.save()
                
                # Enable the feature temporarily
                success = enable_feature_temporary(feature_key.feature)
                
                if success:
                    # Log the activation
                    LicenseLog.objects.create(
                        action='FEATURE_ACTIVATED',
                        feature_key=key,
                        details=f'Feature {feature_key.feature} activated by {request.user}',
                        ip_address=get_client_ip(request),
                        user=request.user if request.user.is_authenticated else None,
                    )
                    messages.success(request, f'Feature "{dict(FEATURE_CHOICES).get(feature_key.feature, feature_key.feature)}" has been activated!')
                else:
                    messages.warning(request, 'Feature activated but may not persist after restart.')
                    
            except FeatureActivationKey.DoesNotExist:
                messages.error(request, 'Invalid activation key.')
            
            return render(request, 'licensing/activate_feature.html', context)
    
    return render(request, 'licensing/activate_feature.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def generate_feature_key_view(request):
    """
    Super Admin view for generating 8-digit activation keys.
    """
    from django.contrib.auth.models import User
    from django.conf import settings
    from .models import FeatureActivationKey, FEATURE_CHOICES
    
    # Only superusers can generate keys
    if not request.user.is_superuser:
        messages.error(request, 'Only super administrators can generate activation keys.')
        return redirect('licensing:management')
    
    context = {
        'features': FEATURE_CHOICES,
    }
    
    # Get existing keys
    context['feature_keys'] = FeatureActivationKey.objects.all()[:20]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_key':
            feature = request.POST.get('feature')
            expiry_hours = int(request.POST.get('expiry_hours', 24))
            
            if not feature:
                messages.error(request, 'Please select a feature.')
                return render(request, 'licensing/generate_feature_key.html', context)
            
            # Generate unique 8-digit key
            import random
            import string
            key = ''.join(random.choices(string.digits, k=8))
            
            # Ensure uniqueness
            while FeatureActivationKey.objects.filter(key=key).exists():
                key = ''.join(random.choices(string.digits, k=8))
            
            # Calculate expiry
            expires_at = timezone.now() + timezone.timedelta(hours=expiry_hours)
            
            # Create the key
            feature_key = FeatureActivationKey.objects.create(
                key=key,
                feature=feature,
                expires_at=expires_at,
                created_by=request.user,
            )
            
            # Log the generation
            LicenseLog.objects.create(
                action='FEATURE_KEY_GENERATED',
                feature_key=key,
                details=f'Key for {feature} generated by {request.user}, expires in {expiry_hours}h',
                ip_address=get_client_ip(request),
                user=request.user,
            )
            
            context['generated_key'] = feature_key
            messages.success(request, f'Activation key generated: {key}')
            
        elif action == 'delete_key':
            key_id = request.POST.get('key_id')
            try:
                fk = FeatureActivationKey.objects.get(id=key_id)
                fk.delete()
                messages.success(request, 'Activation key deleted.')
            except FeatureActivationKey.DoesNotExist:
                messages.error(request, 'Key not found.')
    
    return render(request, 'licensing/generate_feature_key.html', context)


def check_feature_status_api(request):
    """API endpoint to check if a specific feature is enabled."""
    from django.http import JsonResponse
    
    feature = request.GET.get('feature')
    if not feature:
        return JsonResponse({'error': 'Feature parameter required'}, status=400)
    
    features = get_enabled_features()
    is_enabled = feature in features
    
    return JsonResponse({
        'feature': feature,
        'enabled': is_enabled,
        'all_features': features,
    })


# ============================================================================
# FEATURE STATUS HELPERS (for templates)
# ============================================================================

def get_feature_status():
    """Get a dictionary of all features and their status."""
    from .models import FEATURE_CHOICES
    enabled = get_enabled_features()
    
    status = {}
    for code, name in FEATURE_CHOICES:
        status[code] = {
            'name': name,
            'enabled': code in enabled,
            'code': code,
        }
    return status


# ============================================================================
# FEATURE MATRIX ACTIVATION VIEW
# ============================================================================

def feature_matrix_activation_view(request):
    """
    Activate using encrypted feature matrix key.
    """
    from django.shortcuts import render, redirect
    from django.contrib import messages
    from .activation import activate_feature_matrix, check_hwid_match
    from .hwid import get_hwid_short
    from .models import ALL_FEATURES
    
    context = {
        'hwid_short': get_hwid_short(),
        'all_features': ALL_FEATURES,
    }
    
    # Check HWID match
    hwid_ok, hwid_msg = check_hwid_match()
    context['hwid_ok'] = hwid_ok
    context['hwid_message'] = hwid_msg
    
    if request.method == 'POST':
        encrypted_data = request.POST.get('encrypted_data', '').strip()
        signature = request.POST.get('signature', '').strip()
        
        if not encrypted_data or not signature:
            messages.error(request, 'Please provide both encrypted data and signature.')
            return render(request, 'licensing/activate_matrix.html', context)
        
        success, message = activate_feature_matrix(encrypted_data, signature)
        
        if success:
            messages.success(request, message)
            return redirect('licensing:management')
        else:
            messages.error(request, message)
    
    return render(request, 'licensing/activate_matrix.html', context)


# ============================================================================
# EMERGENCY RECOVERY VIEWS
# ============================================================================

def emergency_recovery_view(request):
    """
    Emergency password recovery endpoint.
    Shows challenge code and allows token entry.
    """
    from django.shortcuts import render
    from django.contrib import messages
    from .activation import generate_challenge_code, generate_recovery_token, use_recovery_token
    from .hwid import _get_hardware_id
    from .models import EmergencyRecoveryToken
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    
    context = {}
    
    # Get current HWID and generate challenge
    hwid = _get_hardware_id()
    context['hwid'] = hwid
    context['hwid_short'] = hwid[:8] + '...' + hwid[-4:]
    
    # Generate or get existing challenge
    challenge = generate_challenge_code(hwid)
    context['challenge_code'] = challenge
    
    # Get available users for recovery
    super_admins = User.objects.filter(is_superuser=True)
    context['users'] = super_admins
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_token':
            # Generate a new recovery token
            user_id = request.POST.get('user_id')
            
            try:
                user = User.objects.get(id=user_id, is_superuser=True)
            except User.DoesNotExist:
                messages.error(request, 'Invalid user selected.')
                return render(request, 'licensing/emergency_recovery.html', context)
            
            # Generate token
            token = generate_recovery_token(hwid, challenge)
            expires_at = timezone.now() + timedelta(minutes=30)
            
            # Store token
            EmergencyRecoveryToken.objects.create(
                token=token,
                challenge_code=challenge,
                hwid=hwid,
                expires_at=expires_at,
                created_for_user=user,
            )
            
            context['generated_token'] = token
            context['token_expiry'] = expires_at
            context['recovery_user'] = user.username
            messages.success(request, f'Recovery token generated for {user.username}')
        
        elif action == 'use_token':
            token = request.POST.get('token', '').strip()
            
            if not token:
                messages.error(request, 'Please enter a recovery token.')
                return render(request, 'licensing/emergency_recovery.html', context)
            
            success, message = use_recovery_token(token, challenge, hwid)
            
            if success:
                messages.success(request, message + ' Please login with password: password')
            else:
                messages.error(request, message)
    
    return render(request, 'licensing/emergency_recovery.html', context)
