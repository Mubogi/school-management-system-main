"""Publish/lock, notifications, and promotion workflow."""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import (
    TermReportPublication,
    StudentTermRecord,
    ClassPromotionRule,
    PromotionRun,
    ReportNotificationLog,
    Student,
    AssessmentType,
)
from .report_utils import (
    normalize_report_type,
    assessment_in_report,
    REPORT_MID_TERM,
    class_teacher_comment,
    head_teacher_comment,
)


class MarksLockedError(Exception):
    def __init__(self, message, publication=None):
        super().__init__(message)
        self.publication = publication


def get_publication(school, class_name, term, academic_year, report_type):
    report_type = normalize_report_type(report_type)
    class_name = class_name or ''
    pub, _ = TermReportPublication.objects.get_or_create(
        school=school,
        class_name=class_name,
        term=term,
        academic_year=academic_year,
        report_type=report_type,
        defaults={'is_published': False},
    )
    return pub


def is_report_published(school, class_name, term, academic_year, report_type):
    report_type = normalize_report_type(report_type)
    class_name = class_name or ''
    if TermReportPublication.objects.filter(
        school=school,
        class_name='',
        term=term,
        academic_year=academic_year,
        report_type=report_type,
        is_published=True,
    ).exists():
        return True
    if class_name and TermReportPublication.objects.filter(
        school=school,
        class_name=class_name,
        term=term,
        academic_year=academic_year,
        report_type=report_type,
        is_published=True,
    ).exists():
        return True
    return False


def publish_reports(school, class_name, term, academic_year, report_type, profile):
    pub = get_publication(school, class_name, term, academic_year, report_type)
    pub.is_published = True
    pub.published_at = timezone.now()
    pub.published_by = profile
    pub.save()
    return pub


def unpublish_reports(school, class_name, term, academic_year, report_type, profile):
    pub = get_publication(school, class_name, term, academic_year, report_type)
    pub.is_published = False
    pub.published_at = None
    pub.published_by = profile
    pub.save()
    return pub


def assessment_edit_is_locked(school, class_name, term, academic_year, assessment):
    """True if this assessment cannot be edited due to a published report."""
    for report_type in (TermReportPublication.REPORT_MIDTERM, TermReportPublication.REPORT_EOT):
        if not is_report_published(school, class_name, term, academic_year, report_type):
            continue
        if assessment_in_report(assessment, report_type):
            return True, report_type
    return False, None


def assert_mark_editable(student, assessment, term=None, academic_year=None):
    term = term or student.school.active_term
    academic_year = academic_year or student.school.active_academic_year
    locked, report_type = assessment_edit_is_locked(
        student.school, student.current_class, term, academic_year, assessment
    )
    if locked:
        label = 'Mid-Term' if report_type == REPORT_MID_TERM else 'End of Term'
        raise MarksLockedError(
            f"Marks are locked: {label} reports have been published for "
            f"{student.current_class} ({term}/{academic_year}). "
            f"Contact the Head Teacher to unlock if corrections are needed."
        )


def get_or_init_term_record(student, term=None, academic_year=None):
    term = term or student.school.active_term
    academic_year = academic_year or student.school.active_academic_year
    record, created = StudentTermRecord.objects.get_or_create(
        student=student,
        term=term,
        academic_year=academic_year,
        defaults={'total_school_days': 60},
    )
    return record, created


def apply_term_record_to_report(report_data, term_record=None):
    """Merge saved remarks, attendance, and conduct into report dict."""
    if not term_record:
        student = report_data['student']
        term_record = StudentTermRecord.objects.filter(
            student=student,
            term=report_data['term'],
            academic_year=report_data['academic_year'],
        ).first()

    if term_record:
        if term_record.class_teacher_remark.strip():
            report_data['class_teacher_remark'] = term_record.class_teacher_remark.strip()
        if term_record.head_teacher_remark.strip():
            report_data['head_teacher_remark'] = term_record.head_teacher_remark.strip()
        if term_record.dos_remark.strip():
            report_data['dos_remark'] = term_record.dos_remark.strip()
        report_data['days_present'] = term_record.days_present
        report_data['total_school_days'] = term_record.total_school_days
        report_data['days_absent'] = term_record.days_absent
        report_data['attendance_percent'] = term_record.attendance_percent
        report_data['conduct_rating'] = term_record.get_conduct_rating_display()
        report_data['conduct_note'] = term_record.conduct_note.strip()
    else:
        report_data.setdefault('days_present', 0)
        report_data.setdefault('total_school_days', 60)
        report_data.setdefault('days_absent', 60)
        report_data.setdefault('attendance_percent', 0)
        report_data.setdefault('conduct_rating', 'Good')
        report_data.setdefault('conduct_note', '')
        report_data.setdefault('dos_remark', '')

    report_data.setdefault('dos_remark', report_data.get('dos_remark', ''))
    return report_data


def build_report_download_url(request, student_id, report_type):
    path = f"/pdf/report/{student_id}/{normalize_report_type(report_type)}/"
    return request.build_absolute_uri(path)


def send_bulk_report_emails(students, report_type, term, academic_year, request, sent_by):
    """Send one email per guardian address with all their children's report links."""
    from django.core.mail import EmailMessage

    by_email = {}
    for student in students:
        email = (student.guardian_email or '').strip()
        if not email:
            continue
        by_email.setdefault(email, []).append(student)

    school = sent_by.school if sent_by and sent_by.school else students[0].school
    from_email = (school.email or '').strip() or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@school.local')
    report_type = normalize_report_type(report_type)
    sent_count = 0

    for email, kids in by_email.items():
        guardian = kids[0].guardian_name or 'Parent/Guardian'
        lines = [
            f"Dear {guardian},",
            '',
            f"Please find academic report(s) for {term} {academic_year} from {school.school_name}.",
            '',
        ]
        for student in kids:
            url = build_report_download_url(request, student.student_id, report_type)
            lines.append(f"• {student.first_name} {student.last_name} ({student.student_id}) — Class {student.current_class}")
            lines.append(f"  Download: {url}")
            lines.append('')
        lines.extend([f"Regards,\n{school.school_name}", f"Tel: {school.phone or '—'} | {school.email or ''}"])

        try:
            msg = EmailMessage(
                subject=f"{school.school_name} — Report(s) {term}/{academic_year}",
                body='\n'.join(lines),
                from_email=from_email,
                to=[email],
            )
            msg.send(fail_silently=False)
            for student in kids:
                ReportNotificationLog.objects.create(
                    student=student, term=term, academic_year=academic_year,
                    report_type=report_type, channel=ReportNotificationLog.CHANNEL_EMAIL,
                    recipient=email, status=ReportNotificationLog.STATUS_SENT,
                    detail='Bulk email', sent_by=sent_by,
                )
            sent_count += 1
        except Exception as exc:
            for student in kids:
                ReportNotificationLog.objects.create(
                    student=student, term=term, academic_year=academic_year,
                    report_type=report_type, channel=ReportNotificationLog.CHANNEL_EMAIL,
                    recipient=email, status=ReportNotificationLog.STATUS_FAILED,
                    detail=str(exc), sent_by=sent_by,
                )
    return sent_count


def send_report_email(student, report_type, term, academic_year, request, sent_by):
    report_type = normalize_report_type(report_type)
    email = (student.guardian_email or '').strip()
    if not email:
        ReportNotificationLog.objects.create(
            student=student,
            term=term,
            academic_year=academic_year,
            report_type=report_type,
            channel=ReportNotificationLog.CHANNEL_EMAIL,
            recipient='',
            status=ReportNotificationLog.STATUS_SKIPPED,
            detail='No guardian email on file',
            sent_by=sent_by,
        )
        return False, 'No guardian email'

    url = build_report_download_url(request, student.student_id, report_type)
    school = student.school
    subject = f"{school.school_name} — {student.first_name}'s report ({term}/{academic_year})"
    body = (
        f"Dear {student.guardian_name or 'Parent/Guardian'},\n\n"
        f"Please find your child's academic report for {term} {academic_year}.\n\n"
        f"Student: {student.first_name} {student.last_name} ({student.student_id})\n"
        f"Class: {student.current_class}\n\n"
        f"Download report (PDF):\n{url}\n\n"
        f"Regards,\n{school.school_name}"
    )
    from_email = (school.email or '').strip() or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@school.local')

    try:
        send_mail(subject, body, from_email, [email], fail_silently=False)
        ReportNotificationLog.objects.create(
            student=student,
            term=term,
            academic_year=academic_year,
            report_type=report_type,
            channel=ReportNotificationLog.CHANNEL_EMAIL,
            recipient=email,
            status=ReportNotificationLog.STATUS_SENT,
            detail=f"Link sent: {url}",
            sent_by=sent_by,
        )
        return True, 'Email sent'
    except Exception as exc:
        ReportNotificationLog.objects.create(
            student=student,
            term=term,
            academic_year=academic_year,
            report_type=report_type,
            channel=ReportNotificationLog.CHANNEL_EMAIL,
            recipient=email,
            status=ReportNotificationLog.STATUS_FAILED,
            detail=str(exc),
            sent_by=sent_by,
        )
        return False, str(exc)


def send_report_sms(student, report_type, term, academic_year, request, sent_by):
    """SMS via configurable hook; logs payload for schools without SMS API yet."""
    report_type = normalize_report_type(report_type)
    phone = (student.guardian_phone or '').strip()
    if not phone:
        ReportNotificationLog.objects.create(
            student=student,
            term=term,
            academic_year=academic_year,
            report_type=report_type,
            channel=ReportNotificationLog.CHANNEL_SMS,
            recipient='',
            status=ReportNotificationLog.STATUS_SKIPPED,
            detail='No guardian phone on file',
            sent_by=sent_by,
        )
        return False, 'No guardian phone'

    url = build_report_download_url(request, student.student_id, report_type)
    message = (
        f"{student.school.school_name}: Report for {student.first_name} "
        f"({student.student_id}) {term}/{academic_year}. Download: {url}"
    )

    sms_handler = getattr(settings, 'OFFICEHUB_SMS_HANDLER', None)
    if callable(sms_handler):
        try:
            sms_handler(phone, message)
            status = ReportNotificationLog.STATUS_SENT
            detail = message[:500]
            ok = True
            msg = 'SMS sent'
        except Exception as exc:
            status = ReportNotificationLog.STATUS_FAILED
            detail = str(exc)
            ok = False
            msg = str(exc)
    else:
        # Development: log only (configure OFFICEHUB_SMS_HANDLER for production)
        status = ReportNotificationLog.STATUS_SENT
        detail = f"[Console SMS] To {phone}: {message}"
        ok = True
        msg = 'SMS queued (console mode — set OFFICEHUB_SMS_HANDLER in settings for live SMS)'

    ReportNotificationLog.objects.create(
        student=student,
        term=term,
        academic_year=academic_year,
        report_type=report_type,
        channel=ReportNotificationLog.CHANNEL_SMS,
        recipient=phone,
        status=status,
        detail=detail,
        sent_by=sent_by,
    )
    return ok, msg


def _student_promotion_eligible(student, school, criteria):
    """Return (eligible, reason) based on marks, fees, attendance."""
    from .report_utils import build_student_report_data, student_overall_average, build_subject_rows, filter_marks_for_report
    from .models import MarkEntry, StudentTermRecord

    if not criteria:
        return True, ''

    term = school.active_term
    year = school.active_academic_year
    marks = MarkEntry.objects.filter(student=student, grading_term=term, academic_year=year)
    rows = build_subject_rows(filter_marks_for_report(marks, 'eot'))
    avg = float(student_overall_average(rows))

    if avg < float(criteria.minimum_average):
        return False, f'Average {avg:.1f}% below pass mark {criteria.minimum_average}%'

    if criteria.require_fees_cleared and not student.is_fees_cleared(term, year):
        return False, 'Fees not cleared'

    record = StudentTermRecord.objects.filter(student=student, term=term, academic_year=year).first()
    if record and record.attendance_percent < criteria.minimum_attendance_percent:
        return False, f'Attendance {record.attendance_percent}% below {criteria.minimum_attendance_percent}%'

    return True, ''


def promotion_preview(school):
    """List of {from_class, to_class, students: [...]} for active students."""
    from .models import PromotionCriteria
    rules = {r.from_class: r for r in ClassPromotionRule.objects.filter(school=school)}
    criteria = PromotionCriteria.objects.filter(school=school).first()
    classes = Student.objects.filter(school=school, is_active=True).values_list('current_class', flat=True).distinct()
    preview = []
    for class_name in sorted(set(classes)):
        rule = rules.get(class_name)
        to_class = rule.to_class if rule else '(no rule — unchanged)'
        students = list(
            Student.objects.filter(school=school, current_class=class_name, is_active=True).order_by('last_name')
        )
        student_details = []
        for s in students:
            eligible, reason = _student_promotion_eligible(s, school, criteria) if criteria and criteria.auto_promote_on_year_end else (True, '')
            student_details.append({'student': s, 'eligible': eligible, 'reason': reason})
        preview.append({
            'from_class': class_name,
            'to_class': to_class,
            'has_rule': rule is not None,
            'will_graduate': rule is not None and not rule.to_class,
            'students': students,
            'student_details': student_details,
            'count': len(students),
            'pass_mark': criteria.minimum_average if criteria else None,
        })
    return preview


def run_year_end_promotion(school, to_academic_year, profile, reset_term='T1'):
    from .models import PromotionCriteria
    rules = {r.from_class: r for r in ClassPromotionRule.objects.filter(school=school)}
    criteria = PromotionCriteria.objects.filter(school=school).first()
    promoted = 0
    graduated = 0
    unchanged = 0
    retained = 0

    for student in Student.objects.filter(school=school, is_active=True):
        rule = rules.get(student.current_class)
        if not rule:
            unchanged += 1
            continue
        if criteria and criteria.auto_promote_on_year_end:
            eligible, _ = _student_promotion_eligible(student, school, criteria)
            if not eligible:
                retained += 1
                continue
        if rule.to_class:
            student.current_class = rule.to_class
            student.save(update_fields=['current_class'])
            promoted += 1
        else:
            student.is_active = False
            student.save(update_fields=['is_active'])
            graduated += 1

    from_year = school.active_academic_year
    school.active_academic_year = to_academic_year
    school.active_term = reset_term
    school.save(update_fields=['active_academic_year', 'active_term'])

    run = PromotionRun.objects.create(
        school=school,
        from_academic_year=from_year,
        to_academic_year=to_academic_year,
        students_promoted=promoted,
        students_graduated=graduated,
        run_by=profile,
        notes=f"Unchanged (no rule): {unchanged}. Retained (below criteria): {retained}.",
    )
    return run, promoted, graduated, unchanged, retained


def publication_status_for_classes(school, term, academic_year):
    """Return list of dicts for each class with midterm/eot publish state."""
    from .models import SchoolClass
    classes = list(SchoolClass.objects.filter(school=school).values_list('name', flat=True))

    rows = []
    for class_name in classes:
        row = {'class_name': class_name}
        for rt in (TermReportPublication.REPORT_MIDTERM, TermReportPublication.REPORT_EOT):
            row[f'{rt}_published'] = is_report_published(school, class_name, term, academic_year, rt)
        rows.append(row)

    whole = {}
    for rt in (TermReportPublication.REPORT_MIDTERM, TermReportPublication.REPORT_EOT):
        whole[f'{rt}_published'] = is_report_published(school, '', term, academic_year, rt)
    return rows, whole
