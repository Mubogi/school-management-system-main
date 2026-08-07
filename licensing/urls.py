"""
Licensing URL Configuration
"""
from django.urls import path
from . import views

app_name = 'licensing'

urlpatterns = [
    path('activate/', views.activation_view, name='activate'),
    path('manage/', views.license_management, name='management'),
    path('sessions/', views.session_management, name='session_management'),
    path('sessions/force-logout/', views.force_logout_session, name='force_logout_session'),
    
    # Feature activation
    path('activate-feature/', views.feature_activation_view, name='activate_feature'),
    path('generate-key/', views.generate_feature_key_view, name='generate_key'),
    path('api/check-feature/', views.check_feature_status_api, name='api_check_feature'),
    
    # Feature Matrix (Hardware-bound licensing)
    path('matrix/activate/', views.feature_matrix_activation_view, name='activate_matrix'),
    
    # Emergency Recovery
    path('emergency-recovery/', views.emergency_recovery_view, name='emergency_recovery'),
    
    # API endpoints
    path('api/check/', views.api_check_license, name='api_check'),
    path('api/validate/', views.api_validate_key, name='api_validate'),
]
