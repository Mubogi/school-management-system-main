"""First-boot superuser seeding when the auth User table is empty."""
from django.contrib.auth import get_user_model

from core.models import SchoolConfiguration, UserProfile, PromotionCriteria, StudentIDSequence


DEFAULT_USERNAME = 'jordan'
DEFAULT_PASSWORD = '20020120'
DEFAULT_EMAIL = 'jordan@officehub.school'


def seed_superuser_if_empty():
    User = get_user_model()
    if User.objects.exists():
        return None

    school = SchoolConfiguration.get_school()
    PromotionCriteria.objects.get_or_create(school=school)
    StudentIDSequence.objects.get_or_create(school=school, defaults={'last_number': 0})

    user = User.objects.create_user(
        username=DEFAULT_USERNAME,
        email=DEFAULT_EMAIL,
        password=DEFAULT_PASSWORD,
        first_name='Jordan',
        last_name='Super Admin',
    )
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = 'SUPER_ADMIN'
    profile.school = school
    profile.is_active = True
    profile.save()
    return user
