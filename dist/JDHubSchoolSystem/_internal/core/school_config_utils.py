"""School configuration helpers: term locking, features, grading."""

from django.contrib.auth import get_user_model

from .models import SchoolTermArchive, FeeStructure


def is_term_locked(school, term=None, academic_year=None):
    """Return True if the given term/year is locked for editing."""
    if not school:
        return False
    term = term or school.active_term
    year = academic_year or school.active_academic_year
    if term == school.active_term and year == school.active_academic_year:
        if school.current_term_locked:
            return True
    archive = SchoolTermArchive.objects.filter(
        school=school, term=term, academic_year=year, records_locked=True,
    ).first()
    return archive is not None


def can_edit_term_records(profile, school, term=None, academic_year=None):
    """Super admin can always edit; others blocked when term is locked."""
    if not profile or not school:
        return False
    if profile.role == 'SUPER_ADMIN':
        return True
    return not is_term_locked(school, term, academic_year)


def feature_enabled(school, feature_name):
    if not school or not getattr(school, 'is_active', True):
        return False
    return getattr(school, f'feature_{feature_name}', True)


def carry_fees_to_next_term(school, from_term, from_year, to_term, to_year):
    """Copy fee structures and forward outstanding balances to the next term."""
    structures = FeeStructure.objects.filter(
        school=school, term=from_term, academic_year=from_year,
    )
    for fs in structures:
        FeeStructure.objects.get_or_create(
            school=school,
            target_class=fs.target_class,
            term=to_term,
            academic_year=to_year,
            fee_type=fs.fee_type,
            defaults={
                'school_class': fs.school_class,
                'total_fees_required': fs.total_fees_required,
            },
        )


def close_current_term(school, profile, notes='', carry_fees=None, advance_to_term=None, advance_to_year=None):
    """
    Lock the current term, archive it, and optionally advance to the next period.
    Returns (archive, new_term, new_year).
    """
    term = school.active_term
    year = school.active_academic_year
    carry = carry_fees if carry_fees is not None else school.carry_fees_on_term_close

    archive, _ = SchoolTermArchive.objects.update_or_create(
        school=school, term=term, academic_year=year,
        defaults={
            'reports_published': True,
            'notes': notes,
            'closed_by': profile,
            'records_locked': True,
            'fees_carried_forward': carry,
        },
    )

    school.current_term_locked = True
    school.term_open_for_academics = False
    school.fees_demanded = False

    new_term, new_year = term, year
    if advance_to_term and advance_to_year:
        if carry:
            carry_fees_to_next_term(school, term, year, advance_to_term, advance_to_year)
        school.active_term = advance_to_term
        school.active_academic_year = advance_to_year
        school.current_term_locked = False
        new_term, new_year = advance_to_term, advance_to_year

    school.save()
    return archive, new_term, new_year


def deactivate_user(profile, requester):
    """Deactivate a user account. Super admin can deactivate anyone except themselves."""
    User = get_user_model()
    if profile.user_id == requester.user_id:
        return False, 'You cannot deactivate your own account.'
    profile.is_active = False
    profile.save(update_fields=['is_active'])
    user = profile.user
    user.is_active = False
    user.save(update_fields=['is_active'])
    return True, 'User deactivated.'


def activate_user(profile):
    profile.is_active = True
    profile.save(update_fields=['is_active'])
    user = profile.user
    user.is_active = True
    user.save(update_fields=['is_active'])
    return True, 'User activated.'


def reset_user_password(profile, new_password):
    user = profile.user
    user.set_password(new_password)
    user.save()
    return True, 'Password updated.'
