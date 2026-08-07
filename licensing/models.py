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
