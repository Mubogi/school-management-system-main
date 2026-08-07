# Licensing Module for School Management System

def get_hardware_id():
    from .hwid import _get_hardware_id
    return _get_hardware_id()

def get_machine_id():
    from .hwid import _get_machine_id
    return _get_machine_id()

def is_activated():
    from .activation import _is_activated
    return _is_activated()

def validate_license_key(key, hwid):
    from .activation import _validate_license_key
    return _validate_license_key(key, hwid)

def get_license_status():
    from .activation import _get_license_status
    return _get_license_status()

def get_enabled_features():
    from .activation import _get_enabled_features
    return _get_enabled_features()

def check_feature_access(feature):
    from .activation import _check_feature_access
    return _check_feature_access(feature)

__all__ = [
    'get_hardware_id',
    'get_machine_id',
    'is_activated',
    'validate_license_key',
    'get_license_status',
    'get_enabled_features',
    'check_feature_access',
]
