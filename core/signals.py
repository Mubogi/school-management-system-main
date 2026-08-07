from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.module_loading import import_string

from .models import UserProfile, SchoolConfiguration
from .startup import seed_superuser_if_empty


ROLE_PERMISSIONS = {
    'SUPER_ADMIN': 'ALL',
    'SCHOOL_ADMIN': [
        ('core', 'student', ['add', 'change', 'view']),
        ('core', 'subject', ['add', 'change', 'view']),
        ('core', 'teacher_subject_assignment', ['add', 'change', 'view']),
        ('core', 'feestructure', ['add', 'change', 'view']),
    ],
    'DOS': [
        ('core', 'markentry', ['view', 'change']),
        ('core', 'student', ['view']),
    ],
    'SECRETARY': [
        ('core', 'student', ['add', 'view']),
    ],
    'BURSAR': [
        ('core', 'feepaymentledger', ['add', 'view']),
        ('core', 'feestructure', ['view']),
        ('core', 'student', ['view']),
    ],
    'CLASS_TEACHER': [
        ('core', 'markentry', ['add', 'view']),
        ('core', 'student', ['view']),
    ],
    'SUBJECT_TEACHER': [
        ('core', 'markentry', ['add', 'view']),
        ('core', 'student', ['view']),
    ],
    'HEAD_TEACHER': [
        ('core', 'student', ['view']),
        ('core', 'markentry', ['view']),
    ],
}


def _get_perm(codename):
    try:
        return Permission.objects.filter(codename=codename).first()
    except Permission.DoesNotExist:
        return None


def initialize_roles_and_superadmin():
    """Create groups for roles and a default Super Admin user 'Jordan'."""
    User = get_user_model()

    # Create groups and assign permissions
    for role, perms in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        if perms == 'ALL':
            # give all permissions to this group
            all_perms = Permission.objects.all()
            group.permissions.set(all_perms)
            continue

        perm_objs = []
        for app_label, model_name, actions in perms:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model_name)
            except ContentType.DoesNotExist:
                continue
            for a in actions:
                codename = f"{a}_{model_name}"
                p = _get_perm(codename)
                if p:
                    perm_objs.append(p)

        group.permissions.set(perm_objs)

    # Seed superuser when User table is completely empty (first boot / fresh install)
    try:
        seed_superuser_if_empty()
    except Exception:
        pass


@receiver(post_migrate)
def initialize_on_migrate(sender, app_config, **kwargs):
    if app_config and app_config.name == 'core':
        initialize_roles_and_superadmin()


@receiver(post_save, sender=UserProfile)
def apply_role_permissions(sender, instance: UserProfile, created, **kwargs):
    """When a UserProfile is created or updated, sync Django groups and basic flags."""
    user = instance.user
    role = instance.role
    # Clear existing groups then add the role group
    try:
        user.groups.clear()
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        # Set is_staff for admin roles
        if role in ['SUPER_ADMIN', 'SCHOOL_ADMIN']:
            user.is_staff = True
        else:
            user.is_staff = False
        user.is_active = getattr(instance, 'is_active', True)
        user.save()
    except Exception:
        pass
