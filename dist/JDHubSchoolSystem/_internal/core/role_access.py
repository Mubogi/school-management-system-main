"""Central role checks — SUPER_ADMIN (Jordan) can access every page."""


def user_has_role(profile, allowed_roles):
    if not profile:
        return False
    if profile.role == 'SUPER_ADMIN':
        return True
    return profile.role in allowed_roles


def can_access_view(profile, allowed_roles):
    if not profile or not profile.is_active:
        return False
    if profile.role == 'SUPER_ADMIN':
        return True
    return profile.role in allowed_roles
