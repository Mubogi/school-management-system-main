"""Fee structure lookup and payment helpers (all amounts in Ushs)."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import FeeStructure, FeePaymentLedger, Student, ReceiptSequence, StudentFeeCredit


def term_aliases(term):
    """Generate equivalent term codes (e.g. 1 <-> T1)."""
    term = (term or '').strip()
    aliases = {term}
    if term.upper().startswith('T'):
        aliases.add(term[1:])
        aliases.add(term.upper())
    else:
        aliases.add(f'T{term}')
        aliases.add(f't{term}')
    return [a for a in aliases if a]


def resolve_fee_structure(school, target_class, term, academic_year, fee_type=None):
    fee_type = (fee_type or '').strip()
    for t in term_aliases(term):
        qs = FeeStructure.objects.filter(
            school=school,
            target_class=target_class,
            term=t,
            academic_year=academic_year,
        )
        if fee_type:
            qs = qs.filter(fee_type=fee_type)
        fs = qs.first()
        if fs:
            return fs, t
    if fee_type:
        for t in term_aliases(term):
            fs = FeeStructure.objects.filter(
                school=school,
                target_class=target_class,
                term=t,
                academic_year=academic_year,
            ).first()
            if fs:
                return fs, t
    return None, term


def fee_types_for_class(school, target_class, term=None, academic_year=None):
    term = term or school.active_term
    academic_year = academic_year or school.active_academic_year
    types = set()
    for t in term_aliases(term):
        for ft in FeeStructure.objects.filter(
            school=school,
            target_class=target_class,
            academic_year=academic_year,
            term=t,
        ).values_list('fee_type', flat=True):
            types.add(ft or 'General')
    return sorted(types)


def normalize_term_for_school(school, term=None):
    """Return term string that matches an existing fee structure when possible."""
    term = term or school.active_term
    academic_year = school.active_academic_year
    sample = Student.objects.filter(school=school).values_list('current_class', flat=True).first()
    if sample:
        fs, matched = resolve_fee_structure(school, sample, term, academic_year)
        if fs:
            return matched
    return term


def _next_term(term):
    term = (term or 'T1').strip().upper()
    if term.startswith('T'):
        try:
            n = int(term[1:])
            return f'T{n + 1}'
        except ValueError:
            pass
    try:
        return f'T{int(term) + 1}'
    except ValueError:
        return 'T2'


def _paid_for_fee_type(student, term, academic_year, fee_type):
    qs = FeePaymentLedger.objects.filter(
        student=student,
        academic_year=academic_year,
        term__in=term_aliases(term),
        fee_type=fee_type or '',
    )
    paid = qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    credit = StudentFeeCredit.credit_total(student, term, academic_year, fee_type=fee_type or None)
    return paid + credit


def create_payment_record(
    student,
    amount,
    recorded_by=None,
    term=None,
    academic_year=None,
    payment_mode='CASH',
    fee_type=None,
    excess_action=None,
    excess_fee_type=None,
):
    school = student.school
    term = term or school.active_term
    academic_year = academic_year or school.active_academic_year
    amount = Decimal(amount).quantize(Decimal('0.01'))

    fee_struct, matched_term = resolve_fee_structure(
        school, student.current_class, term, academic_year, fee_type=fee_type,
    )
    if not fee_struct:
        raise ValueError(
            f'No fee structure for class {student.current_class}, term {term}, '
            f'year {academic_year}' + (f', type {fee_type}' if fee_type else '')
        )

    term = matched_term
    fee_type_label = fee_struct.fee_type or 'General'
    total_required = fee_struct.compute_total()
    already_paid = _paid_for_fee_type(student, term, academic_year, fee_type_label)
    remaining_before = (total_required - already_paid).quantize(Decimal('0.01'))

    apply_amount = min(amount, max(remaining_before, Decimal('0.00')))
    if apply_amount <= Decimal('0.00') and amount > Decimal('0.00'):
        apply_amount = amount
    excess = (amount - apply_amount).quantize(Decimal('0.01'))

    with transaction.atomic():
        seq_obj, _ = ReceiptSequence.objects.select_for_update().get_or_create(
            school=school, year=academic_year, term=term,
        )
        seq_obj.last_seq += 1
        seq_obj.save()
        seq_no = str(seq_obj.last_seq).zfill(5)
        receipt = f"OS-{academic_year}-{term}-{seq_no}"

        overall_balance = student.balance(term, academic_year)
        if overall_balance is None:
            overall_balance = Decimal('0.00')
        balance_after = (overall_balance - amount).quantize(Decimal('0.01'))

        payment = FeePaymentLedger.objects.create(
            student=student,
            amount_paid=amount,
            balance_remaining=balance_after,
            fee_type=fee_type_label,
            unique_receipt_id=receipt,
            recorded_by=recorded_by,
            term=term,
            academic_year=academic_year,
            payment_mode=payment_mode,
        )

        if excess > Decimal('0.00'):
            action = (excess_action or '').strip()
            if action == 'next_term':
                next_term = _next_term(term)
                next_year = academic_year
                if next_term in ('T4', '4', 'T5'):
                    try:
                        next_year = str(int(academic_year) + 1)
                        next_term = 'T1'
                    except (TypeError, ValueError):
                        next_term = 'T1'
                StudentFeeCredit.objects.create(
                    student=student,
                    amount=excess,
                    fee_type='',
                    term=next_term,
                    academic_year=next_year,
                    notes=f'Forwarded from receipt {receipt}',
                )
            elif action == 'other_fee' and excess_fee_type:
                FeePaymentLedger.objects.create(
                    student=student,
                    amount_paid=excess,
                    balance_remaining=balance_after,
                    fee_type=excess_fee_type,
                    unique_receipt_id=f'{receipt}-X',
                    recorded_by=recorded_by,
                    term=term,
                    academic_year=academic_year,
                    payment_mode=payment_mode,
                )
            elif excess_fee_type:
                StudentFeeCredit.objects.create(
                    student=student,
                    amount=excess,
                    fee_type=excess_fee_type,
                    term=term,
                    academic_year=academic_year,
                    notes=f'Excess from receipt {receipt}',
                )

    return payment


def payment_context_for_receipt(payment):
    """Extra fields for receipt / PDF templates."""
    student = payment.student
    school = student.school
    term = payment.term or school.active_term
    year = payment.academic_year or school.active_academic_year
    fee_struct, _ = resolve_fee_structure(
        school, student.current_class, term, year, fee_type=payment.fee_type or None,
    )
    total_required = student.total_fees_required(term, year)
    paid = student.total_paid(term, year)
    return {
        'total_fees': total_required,
        'total_paid_after': paid,
        'fee_type': payment.fee_type or (fee_struct.fee_type if fee_struct else ''),
        'currency': 'Ushs',
    }


def record_payment_from_form(request, form, profile):
    """Validate form and create payment; returns (payment, form) or (None, form) on error."""
    from django.contrib import messages

    if not form.is_valid():
        return None, form
    try:
        payment = FeePaymentLedger.create_payment(
            student=form.cleaned_data['student'],
            amount=form.cleaned_data['amount'],
            recorded_by=profile,
            payment_mode=form.cleaned_data.get('payment_mode', 'CASH'),
            fee_type=form.cleaned_data.get('fee_type'),
            excess_action=form.cleaned_data.get('excess_action'),
            excess_fee_type=form.cleaned_data.get('excess_fee_type'),
        )
        return payment, form
    except ValueError as exc:
        messages.error(request, str(exc))
        return None, form


def build_cleared_and_outstanding(school):
    """Return (cleared_list, outstanding_list) for financial reports."""
    cleared = []
    outstanding = []
    for student in Student.objects.filter(school=school, is_active=True).order_by('current_class', 'last_name'):
        balance = student.balance()
        entry = {
            'student': student,
            'balance': balance or Decimal('0.00'),
            'total_required': student.total_fees_required(),
            'total_paid': student.total_paid(),
        }
        if balance is None:
            continue
        if balance <= Decimal('0.00'):
            cleared.append(entry)
        else:
            outstanding.append(entry)
    return cleared, outstanding
