"""
Feature Access & License Decorators
Use @feature_required('feature_name') or @license_required('tier_name') to protect views.
"""
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse, Http404
from django.shortcuts import redirect


# License tier hierarchy
TIER_HIERARCHY = {
    'BASIC': 1,
    'STANDARD': 2,
    'PREMIUM': 3,
}


def license_required(*required_tiers, **kwargs):
    """
    Decorator to require specific license tiers for a view.
    Supports tier hierarchy - a higher tier grants access to lower tier views.
    
    Usage:
        @license_required('BASIC')
        def basic_view(request):  # Accessible by BASIC, STANDARD, PREMIUM
        
        @license_required('STANDARD')
        def standard_view(request):  # Accessible by STANDARD, PREMIUM only
        
        @license_required('PREMIUM')
        def premium_view(request):  # Accessible by PREMIUM only
    
    Options:
        - redirect_to: URL to redirect to if tier not met (default: /licensing/activate/)
        - ajax_response: Return JSON error for AJAX requests (default: True)
    """
    redirect_to = kwargs.get('redirect_to', '/licensing/activate/')
    ajax_response = kwargs.get('ajax_response', True)
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .activation import _get_license_status
            
            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Get current license status
            status = _get_license_status()
            current_tier = status.get('tier', 'NONE')
            
            # Check if any of the required tiers is met
            tier_met = False
            for required in required_tiers:
                # Check if current tier is at least the required tier
                current_level = TIER_HIERARCHY.get(current_tier, 0)
                required_level = TIER_HIERARCHY.get(required, 0)
                
                if current_level >= required_level and current_level > 0:
                    tier_met = True
                    break
            
            if not tier_met:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and ajax_response:
                    return JsonResponse({
                        'error': f'License tier required: {", ".join(required_tiers)}',
                        'code': 'TIER_REQUIRED',
                        'current_tier': current_tier,
                        'required_tiers': list(required_tiers),
                    }, status=403)
                
                return HttpResponseForbidden(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Upgrade Required</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="bg-light d-flex align-items-center justify-content-center" style="min-height: 100vh;">
                    <div class="text-center">
                        <div class="card shadow-lg" style="max-width: 500px;">
                            <div class="card-body p-5">
                                <i class="bi bi-shield-lock text-warning fs-1 mb-3 d-block"></i>
                                <h3 class="card-title mb-3">License Upgrade Required</h3>
                                <p class="text-muted mb-4">
                                    This feature requires a <strong>{'/'.join(required_tiers)}</strong> license or higher.
                                    <br>Your current license: <span class="badge bg-secondary">{current_tier}</span>
                                </p>
                                <a href="/licensing/activate/" class="btn btn-primary">
                                    <i class="bi bi-rocket-takeoff me-2"></i>Upgrade License
                                </a>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def feature_required(*features, **kwargs):
    """
    Decorator to require specific features for a view.
    
    Usage:
        @feature_required('fees')
        def bursar_view(request):
            ...
        
        @feature_required('fees', 'marks')
        def academic_view(request):
            ...
    
    Options:
        - redirect_to: URL to redirect to if feature not available (default: /activate/)
        - ajax_response: Return JSON error for AJAX requests (default: True)
    """
    redirect_to = kwargs.get('redirect_to', '/activate/')
    ajax_response = kwargs.get('ajax_response', True)
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .activation import _check_feature_access, _is_activated, _get_enabled_features
            
            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check if system is activated
            if not _is_activated():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and ajax_response:
                    return JsonResponse({
                        'error': 'System not activated',
                        'code': 'NOT_ACTIVATED',
                        'redirect': redirect_to
                    }, status=403)
                return redirect(redirect_to)
            
            # Check each required feature
            enabled_features = _get_enabled_features()
            
            for feature in features:
                if feature not in enabled_features:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and ajax_response:
                        return JsonResponse({
                            'error': f'Feature not available: {feature}',
                            'code': 'FEATURE_LOCKED',
                            'required': list(features),
                            'enabled': enabled_features
                        }, status=403)
                    
                    # Return a proper 403 or redirect to upgrade page
                    return HttpResponseForbidden(
                        f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                            <h2 style="color: #e74c3c;">Feature Locked</h2>
                            <p>The feature "<strong>{feature}</strong>" is not available in your current license.</p>
                            <p>Please upgrade your license to access this feature.</p>
                            <a href="/activate/" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                                Manage License
                            </a>
                        </body>
                        </html>
                        """
                    )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def tier_required(*tiers):
    """
    Decorator to require specific license tiers.
    
    Usage:
        @tier_required('PREMIUM')
        def premium_feature(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .activation import _get_license_status
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            status = _get_license_status()
            current_tier = status.get('tier', 'NONE')
            
            if current_tier not in tiers:
                return HttpResponseForbidden(
                    f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                        <h2 style="color: #e74c3c;">License Tier Required</h2>
                        <p>This feature requires: {', '.join(tiers)}</p>
                        <p>Your current tier: <strong>{current_tier}</strong></p>
                        <a href="/activate/" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            Upgrade License
                        </a>
                    </body>
                    </html>
                    """
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def check_feature(feature):
    """
    Simple decorator that passes feature check result to view.
    
    Usage:
        @check_feature('fees')
        def bursar_view(request, feature_allowed=True):
            if not feature_allowed:
                return redirect('/activate/')
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .activation import _check_feature_access
            
            feature_allowed = (
                request.user.is_superuser or 
                _check_feature_access(feature)
            )
            
            # Add to kwargs so view can use it
            kwargs['feature_allowed'] = feature_allowed
            kwargs['feature_name'] = feature
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
