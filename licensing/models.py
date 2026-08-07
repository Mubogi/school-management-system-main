"""
License Models for storing activation data.
"""
from django.db import models
from django.utils import timezone


class LicenseKey(models.Model):
    """Model for storing generated license keys."""
    
    TIER_CHOICES = [
        ('BASIC', 'Basic'),
        ('STANDARD', 'Standard'),
        ('PREMIUM', 'Premium'),
        ('DEMO', 'Demo'),
    ]
    
    key = models.CharField(max_length=50, unique=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    features = models.TextField(help_text="Comma-separated list of enabled features")
    duration_days = models.IntegerField(default=30)
    max_activations = models.IntegerField(default=1)
    activation_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "License Key"
        verbose_name_plural = "License Keys"
    
    def __str__(self):
        return f"{self.key} ({self.tier})"
    
    def is_valid(self):
        """Check if this license key can still be activated."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.activation_count >= self.max_activations:
            return False
        return True


class LicenseActivation(models.Model):
    """Model for tracking license activations per installation."""
    
    license_key = models.CharField(max_length=50)
    tier = models.CharField(max_length=20)
    enabled_features = models.TextField(help_text="Comma-separated list of enabled features")
    expires_at = models.DateTimeField(null=True, blank=True)
    hwid_bound = models.CharField(max_length=50, null=True, blank=True, 
                                  help_text="Hardware ID if HWID binding is enabled")
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    machine_name = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = "License Activation"
        verbose_name_plural = "License Activations"
    
    def __str__(self):
        return f"{self.license_key} - {self.tier} ({self.activated_at})"
    
    def is_expired(self):
        """Check if the activation has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < timezone.now()


class LicenseLog(models.Model):
    """Audit log for license-related events."""
    
    ACTION_CHOICES = [
        ('ACTIVATED', 'License Activated'),
        ('DEACTIVATED', 'License Deactivated'),
        ('VERIFIED', 'License Verified'),
        ('EXPIRED', 'License Expired'),
        ('FAILED', 'Activation Failed'),
    ]
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    license_key = models.CharField(max_length=50, blank=True)
    hwid = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "License Log"
        verbose_name_plural = "License Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.created_at}"


class AuditLog(models.Model):
    """
    Comprehensive audit log for tracking user actions across the system.
    Records student modifications, fee changes, report generation, etc.
    """
    
    ACTION_CHOICES = [
        # Student actions
        ('STUDENT_CREATE', 'Student Created'),
        ('STUDENT_UPDATE', 'Student Updated'),
        ('STUDENT_DELETE', 'Student Deleted'),
        ('STUDENT_PROMOTE', 'Student Promoted'),
        ('STUDENT_ARCHIVE', 'Student Archived'),
        ('STUDENT_GRADUATE', 'Student Graduated'),
        
        # Fee actions
        ('FEE_PAYMENT', 'Fee Payment Recorded'),
        ('FEE_STRUCTURE_CREATE', 'Fee Structure Created'),
        ('FEE_STRUCTURE_UPDATE', 'Fee Structure Updated'),
        ('FEE_REFUND', 'Fee Refund Processed'),
        
        # Report actions
        ('REPORT_GENERATE', 'Report Generated'),
        ('REPORT_PRINT', 'Report Printed'),
        ('REPORT_EXPORT', 'Report Exported'),
        ('REPORT_PUBLISH', 'Report Published'),
        
        # User actions
        ('USER_LOGIN', 'User Logged In'),
        ('USER_LOGOUT', 'User Logged Out'),
        ('USER_CREATE', 'User Created'),
        ('USER_UPDATE', 'User Updated'),
        ('PASSWORD_CHANGE', 'Password Changed'),
        
        # Academic actions
        ('MARK_ENTRY', 'Marks Entered'),
        ('MARK_UPDATE', 'Marks Updated'),
        ('ATTENDANCE_MARK', 'Attendance Marked'),
        ('REMARK_ADDED', 'Remark Added'),
        
        # Admin actions
        ('SETTINGS_CHANGE', 'Settings Changed'),
        ('BACKUP_CREATE', 'Backup Created'),
        ('IMPORT_DATA', 'Data Imported'),
        ('EXPORT_DATA', 'Data Exported'),
        
        # Session actions
        ('SESSION_TERMINATE', 'Session Terminated'),
    ]
    
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    description = models.TextField(blank=True, default='')
    
    # Actor
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    username = models.CharField(max_length=150, blank=True)
    
    # Target
    target_type = models.CharField(max_length=50, blank=True, db_index=True)
    target_id = models.CharField(max_length=100, blank=True, db_index=True)
    target_name = models.CharField(max_length=255, blank=True)
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    session_key = models.CharField(max_length=40, blank=True)
    
    # Change tracking
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    
    # Metadata
    school = models.ForeignKey(
        'core.SchoolConfiguration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    academic_year = models.CharField(max_length=20, blank=True)
    term = models.CharField(max_length=10, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} by {self.username or 'System'} at {self.created_at:%Y-%m-%d %H:%M}"
    
    @classmethod
    def log(cls, action, user=None, target_type='', target_id='', target_name='',
            description='', request=None, old_value=None, new_value=None, school=None):
        """Helper method to create audit log entries."""
        kwargs = {
            'action': action,
            'user': user,
            'username': user.username if user else 'System',
            'target_type': target_type,
            'target_id': target_id,
            'target_name': target_name,
            'description': description,
            'old_value': old_value,
            'new_value': new_value,
        }
        
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                kwargs['ip_address'] = x_forwarded_for.split(',')[0].strip()
            else:
                kwargs['ip_address'] = request.META.get('REMOTE_ADDR')
            kwargs['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
            kwargs['session_key'] = request.session.session_key or ''
            
            if school is None:
                school = getattr(request, 'school', None)
        
        if school:
            kwargs['school'] = school
            kwargs['academic_year'] = school.active_academic_year or ''
            kwargs['term'] = school.active_term or ''
        
        return cls.objects.create(**kwargs)
