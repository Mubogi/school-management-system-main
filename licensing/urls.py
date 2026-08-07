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
    
    # API endpoints
    path('api/check/', views.api_check_license, name='api_check'),
    path('api/validate/', views.api_validate_key, name='api_validate'),
]
