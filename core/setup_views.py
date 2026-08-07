"""
First-Run Setup Wizard Views
Handles initial system configuration when no admin exists.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.views import View
from django.utils import timezone

from licensing.hwid import _get_hardware_id
from core.models import SchoolConfiguration

User = get_user_model()


class SetupWizardView(View):
    """
    First-run setup wizard that creates the initial admin account
    and configures the school.
    """
    template_name = 'core/setup_wizard.html'
    
    def get(self, request):
        # Get or set current step
        step = int(request.GET.get('step', 1))
        
        # Check if setup is already complete (admin exists)
        admin_exists = User.objects.filter(is_superuser=True).exists()
        
        if admin_exists and step < 3:
            # Setup already done, redirect to login
            messages.info(request, 'System is already configured. Please login.')
            return redirect('core:login')
        
        # Get HWID
        hwid = _get_hardware_id()
        
        context = {
            'step': step,
            'hwid': hwid,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        step = int(request.POST.get('step', 1))
        hwid = _get_hardware_id()
        
        if step == 1:
            return self._handle_step1(request, hwid)
        elif step == 2:
            return self._handle_step2(request, hwid)
        
        return redirect('core:setup_wizard')
    
    def _handle_step1(self, request, hwid):
        """Handle admin account creation."""
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Validate passwords
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return redirect(f'{request.path}?step=1')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return redirect(f'{request.path}?step=1')
        
        # Store in session
        request.session['setup_password'] = password
        
        context = {
            'step': 2,
            'hwid': hwid,
        }
        return render(request, self.template_name, context)
    
    def _handle_step2(self, request, hwid):
        """Handle school configuration."""
        password = request.session.get('setup_password')
        
        if not password:
            messages.error(request, 'Please complete step 1 first.')
            return redirect(f'{request.path}?step=1')
        
        # Get school details
        school_name = request.POST.get('school_name', '').strip()
        school_initials = request.POST.get('school_initials', '').strip().upper()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        
        if not school_name:
            messages.error(request, 'School name is required.')
            return redirect(f'{request.path}?step=2')
        
        if not school_initials:
            messages.error(request, 'School initials are required.')
            return redirect(f'{request.path}?step=2')
        
        # Create superuser
        try:
            user = User.objects.create(
                username='Jordan',
                password=make_password(password),
                first_name='Jordan',
                last_name='Admin',
                email='admin@school.local',
                is_superuser=True,
                is_staff=True,
                is_active=True,
            )
            
            # Create user profile with MASTER_VENDOR role
            from core.models import UserProfile
            UserProfile.objects.create(
                user=user,
                role='MASTER_VENDOR',
                is_active=True,
            )
            
        except Exception as e:
            messages.error(request, f'Failed to create admin: {str(e)}')
            return redirect(f'{request.path}?step=1')
        
        # Create or update school configuration
        try:
            school = SchoolConfiguration.get_school()
            school.school_name = school_name
            school.school_initials_prefix = school_initials
            school.address = address
            school.phone = phone
            school.email = email
            school.is_active = True
            school.save()
        except Exception as e:
            messages.warning(request, f'School config partial: {str(e)}')
        
        # Create default license activation
        try:
            from licensing.models import LicenseActivation
            LicenseActivation.objects.create(
                license_key='SMS-DEMO-2026-BASIC-XXXX',
                tier='DEMO',
                enabled_features='students,staff,basic_reports',
                expires_at=timezone.now() + timezone.timedelta(days=7),
                is_active=True,
                activated_at=timezone.now(),
            )
        except Exception:
            pass
        
        # Clear session
        if 'setup_password' in request.session:
            del request.session['setup_password']
        
        context = {
            'step': 3,
            'hwid': hwid,
        }
        return render(request, self.template_name, context)


def check_first_run(request):
    """
    Middleware-like check: redirect to setup if no admin exists.
    Call this at the start of any view that requires authentication.
    """
    admin_exists = User.objects.filter(is_superuser=True).exists()
    
    if not admin_exists:
        return redirect('core:setup_wizard')
    
    return None
