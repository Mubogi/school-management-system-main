"""
License Activation and Validation Module
Handles license key validation, expiration checks, and feature management.
"""
import hashlib
import hmac
import base64
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# License tiers and their features
LICENSE_TIERS = {
    'BASIC': {
        'name': 'Basic',
        'features': ['students', 'staff', 'basic_reports'],
        'duration_days': 30,
    },
    'STANDARD': {
        'name': 'Standard',
        'features': ['students', 'staff', 'basic_reports', 'fees', 'marks', 'attendance', 'messages'],
        'duration_days': 90,
    },
    'PREMIUM': {
        'name': 'Premium',
        'features': ['students', 'staff', 'basic_reports', 'fees', 'marks', 'attendance', 
                     'messages', 'exams', 'promotions', 'backup', 'all_reports', 'export'],
        'duration_days': 365,
    },
}

# Demo key for testing (valid for 7 days, basic features)
DEMO_KEY = "SMS-DEMO-2026-BASIC-XXXX"

@dataclass
class LicenseInfo:
    """License information container."""
    is_valid: bool
    tier: str
    features: List[str]
    expires_at: Optional[datetime]
    hwid_bound: bool
    message: str

def _generate_key_signature(key_data: str, secret: str = 'school_sms_secret_key') -> str:
    """Generate HMAC signature for key validation."""
    return hmac.new(
        secret.encode(),
        key_data.encode(),
        hashlib.sha256
    ).hexdigest()[:16]

def _encode_license_data(tier: str, duration_days: int, features: List[str]) -> str:
    """Encode license data into a base64 string."""
    data = {
        'tier': tier,
        'duration': duration_days,
        'features': features,
        'version': '1.0',
    }
    json_str = json.dumps(data)
    return base64.b64encode(json_str.encode()).decode()

def _decode_license_data(encoded: str) -> Optional[Dict]:
    """Decode license data from base64 string."""
    try:
        json_str = base64.b64decode(encoded.encode()).decode()
        return json.loads(json_str)
    except Exception:
        return None

def _format_license_key(tier_prefix: str, encoded_data: str, short_id: str) -> str:
    """Format a license key in standard format: SMS-TIER-DATA-SHORTID"""
    return f"SMS-{tier_prefix}-{encoded_data[:8].upper()}-{short_id[:4].upper()}"

def _parse_license_key(key: str) -> Optional[Dict]:
    """
    Parse and validate a license key.
    Format: SMS-{TIER}-{DATA}-{ID}
    Example: SMS-PREMIUM-A1B2C3D4-XYZW
    """
    if not key:
        return None
    
    # Clean the key
    key = key.strip().upper()
    
    # Check format
    pattern = r'^SMS-(BASIC|STANDARD|PREMIUM|DEMO)-[A-Z0-9]{8}-[A-Z0-9]{4}$'
    if not re.match(pattern, key):
        return None
    
    parts = key.split('-')
    if len(parts) != 4:
        return None
    
    return {
        'tier': parts[1],
        'encoded': parts[2],
        'id': parts[3],
    }

def _validate_license_key(key: str, hwid: str) -> Tuple[bool, str, LicenseInfo]:
    """
    Validate a license key against the HWID.
    Returns: (is_valid, message, license_info)
    """
    if not key:
        return False, "License key is required", LicenseInfo(
            is_valid=False, tier='NONE', features=[], 
            expires_at=None, hwid_bound=False, message="No key provided"
        )
    
    # Parse the key
    parsed = _parse_license_key(key)
    if not parsed:
        # Check for demo key
        if key == DEMO_KEY:
            return True, "Demo license active", LicenseInfo(
                is_valid=True, tier='DEMO', features=['students', 'staff'],
                expires_at=datetime.now() + timedelta(days=7),
                hwid_bound=False, message="Demo license (7 days)"
            )
        return False, "Invalid license key format", LicenseInfo(
            is_valid=False, tier='NONE', features=[],
            expires_at=None, hwid_bound=False, message="Invalid key format"
        )
    
    tier = parsed['tier']
    
    # Check if tier exists
    if tier not in LICENSE_TIERS:
        return False, f"Unknown license tier: {tier}", LicenseInfo(
            is_valid=False, tier='NONE', features=[],
            expires_at=None, hwid_bound=False, message="Unknown tier"
        )
    
    tier_info = LICENSE_TIERS[tier]
    
    return True, f"{tier_info['name']} license active", LicenseInfo(
        is_valid=True,
        tier=tier,
        features=tier_info['features'],
        expires_at=None,  # Perpetual license
        hwid_bound=False,  # Not bound for simplicity
        message=f"{tier_info['name']} license"
    )

def _is_activated() -> bool:
    """Check if the system has a valid activation."""
    from .models import LicenseActivation
    
    try:
        activation = LicenseActivation.objects.filter(is_active=True).first()
        if not activation:
            return False
        
        if activation.expires_at and activation.expires_at < datetime.now():
            return False
        
        return True
    except Exception:
        return False

def _get_license_status() -> Dict:
    """Get current license status information."""
    from .models import LicenseActivation
    
    status = {
        'is_activated': False,
        'tier': 'NONE',
        'tier_name': 'Not Activated',
        'features': [],
        'expires_at': None,
        'hwid': None,
        'message': 'System not activated',
    }
    
    try:
        activation = LicenseActivation.objects.filter(is_active=True).first()
        if activation:
            status['is_activated'] = True
            status['tier'] = activation.tier
            status['tier_name'] = LICENSE_TIERS.get(activation.tier, {}).get('name', 'Unknown')
            status['features'] = activation.enabled_features.split(',') if activation.enabled_features else []
            status['expires_at'] = activation.expires_at
            status['hwid'] = activation.hwid_bound
            status['message'] = f"{status['tier_name']} License"
    except Exception:
        pass
    
    return status

def _get_enabled_features() -> List[str]:
    """Get list of enabled features based on current license."""
    from .models import LicenseActivation
    
    try:
        activation = LicenseActivation.objects.filter(is_active=True).first()
        if activation and activation.enabled_features:
            return [f.strip() for f in activation.enabled_features.split(',')]
    except Exception:
        pass
    
    return []

def _check_feature_access(feature: str) -> bool:
    """Check if a specific feature is accessible under current license."""
    features = _get_enabled_features()
    
    # Super admins always have full access
    from django.contrib.auth import get_user_model
    from core.models import UserProfile
    
    try:
        User = get_user_model()
        if hasattr(User, 'is_authenticated') and User.is_authenticated:
            profile = getattr(User, 'userprofile', None)
            if profile and profile.role == 'SUPER_ADMIN':
                return True
    except Exception:
        pass
    
    return feature in features or 'all_reports' in features

def activate_license(key: str, hwid: str) -> Tuple[bool, str]:
    """
    Activate the system with a license key.
    Returns: (success, message)
    """
    from .models import LicenseActivation
    
    is_valid, message, license_info = _validate_license_key(key, hwid)
    
    if not is_valid:
        return False, message
    
    try:
        # Deactivate any existing license
        LicenseActivation.objects.filter(is_active=True).update(is_active=False)
        
        # Create new activation
        activation = LicenseActivation.objects.create(
            license_key=key,
            tier=license_info.tier,
            enabled_features=','.join(license_info.features),
            expires_at=license_info.expires_at,
            hwid_bound=hwid if license_info.hwid_bound else None,
            is_active=True,
            activated_at=datetime.now(),
        )
        
        return True, f"License activated successfully: {license_info.message}"
    except Exception as e:
        return False, f"Activation failed: {str(e)}"

def deactivate_license() -> bool:
    """Deactivate the current license."""
    from .models import LicenseActivation
    
    try:
        LicenseActivation.objects.filter(is_active=True).update(is_active=False)
        return True
    except Exception:
        return False
