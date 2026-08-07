"""
License Check Middleware
Redirects unactivated or expired systems to activation screen.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse


class LicenseCheckMiddleware:
    """
    Middleware to check license status on every request.
    Redirects to activation page if system is not activated.
    """
    
    # Paths that don't require license check
    EXEMPT_PATHS = [
        '/activate/',
        '/accounts/login/',
        '/accounts/logout/',
        '/admin/',
        '/static/',
        '/media/',
        '/sw.js',
        '/manifest.json',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip check for exempt paths
        path = request.path
        
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return self.get_response(request)
        
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip for superuser (can always access admin functions)
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Check license status
        from .activation import _is_activated
        from .models import LicenseActivation
        
        try:
            # Check if there's an active, non-expired license
            activation = LicenseActivation.objects.filter(is_active=True).first()
            
            if not activation:
                return redirect('licensing:activate')
            
            if activation.expires_at and activation.expires_at.replace(tzinfo=None) < __import__('datetime').datetime.now():
                return redirect('licensing:activate')
                
        except Exception:
            # If there's any error checking license, allow access
            # (prevents lockout during setup)
            pass
        
        return self.get_response(request)


class FeatureAccessMiddleware:
    """
    Middleware to enforce feature-level access control.
    Works with @feature_required decorator.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store feature access info in request for views to use
        request.license_features = self._get_enabled_features(request)
        return self.get_response(request)
    
    def _get_enabled_features(self, request):
        """Get list of features enabled for this request."""
        from .activation import _get_enabled_features
        
        if request.user.is_superuser:
            # Return all possible features for superusers
            return ['students', 'staff', 'basic_reports', 'fees', 'marks', 
                    'attendance', 'messages', 'exams', 'promotions', 
                    'backup', 'all_reports', 'export']
        
        return _get_enabled_features()
