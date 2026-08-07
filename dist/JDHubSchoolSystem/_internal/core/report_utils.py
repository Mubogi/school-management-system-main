"""Report building, automatic comments, and analytics data for OfficeHub."""
from decimal import Decimal
from collections import defaultdict

from .models import MarkEntry, Student, Subject, grade_from_score

REPORT_MID_TERM = 'midterm'
REPORT_END_TERM = 'eot'
REPORT_FULL = 'full'

MID_TERM_KEYWORDS = ('mid', 'mid-term', 'midterm')
EOT_EXTRA_KEYWORDS = ('end', 'exam', 'final', 'eot')


def normalize_report_type(report_type):
    if not report_type:
        return REPORT_END_TERM
    key = str(report_type).lower().strip()
    if key in ('mid', 'midterm', 'mid-term', REPORT_MID_TERM):
        return REPORT_MID_TERM
    if key in ('eot', 'end', 'endterm', 'end-of-term', REPORT_END_TERM, REPORT_FULL, 'full'):
        return REPORT_END_TERM
    return REPORT_END_TERM


def report_type_label(report_type):
    if report_type == REPORT_MID_TERM:
        return 'Mid-Term Report'
    return 'End of Term Report'


def assessment_in_report(assessment, report_type):
    name = assessment.name.lower()
    if report_type == REPORT_MID_TERM:
        return any(k in name for k in MID_TERM_KEYWORDS)
    return True


def filter_marks_for_report(marks_qs, report_type):
    report_type = normalize_report_type(report_type)
    if report_type == REPORT_MID_TERM:
        return [m for m in marks_qs if assessment_in_report(m.assessment_type, report_type)]
    return list(marks_qs)


def build_subject_rows(marks):
    """Aggregate marks per subject with per-assessment breakdown."""
    subject_map = {}
    for m in marks:
        key = m.subject.id
        entry = subject_map.setdefault(key, {
            'subject': m.subject,
            'assessments': [],
            'weighted': Decimal('0.00'),
            'raw_scores': [],
        })
        entry['assessments'].append({
            'name': m.assessment_type.name,
            'score': m.score_achieved,
            'weight': m.assessment_type.weight_percentage,
            'grade': m.grade(),
        })
        entry['weighted'] += m.weighted_score()
        entry['raw_scores'].append(Decimal(m.score_achieved))

    rows = []
    for entry in subject_map.values():
        avg_raw = (
            sum(entry['raw_scores']) / len(entry['raw_scores'])
            if entry['raw_scores'] else Decimal('0.00')
        )
        weighted = entry['weighted']
        rows.append({
            'subject': entry['subject'],
            'assessments': entry['assessments'],
            'average_raw': avg_raw.quantize(Decimal('0.01')),
            'weighted': weighted.quantize(Decimal('0.01')),
            'grade': grade_from_score(float(weighted)),
        })
    rows.sort(key=lambda r: r['subject'].name)
    return rows


def student_overall_average(subject_rows):
    if not subject_rows:
        return Decimal('0.00')
    total = sum(r['weighted'] for r in subject_rows)
    return (total / len(subject_rows)).quantize(Decimal('0.01'))


def class_teacher_comment(avg_percent):
    score = float(avg_percent)
    if score >= 80:
        return (
            f"{avg_percent}% average — excellent work this term. "
            "Keep up the strong effort, discipline, and participation in class."
        )
    if score >= 70:
        return (
            f"{avg_percent}% average — very good progress. "
            "Continue revising regularly and aim for consistency across all subjects."
        )
    if score >= 60:
        return (
            f"{avg_percent}% average — satisfactory performance. "
            "More focus on weak subjects and homework completion is encouraged."
        )
    if score >= 50:
        return (
            f"{avg_percent}% average — fair effort shown. "
            "Greater commitment to class work and consultation with teachers is advised."
        )
    return (
        f"{avg_percent}% average — below expected standard. "
        "Parents are urged to support closer supervision and remedial work at home."
    )


def head_teacher_comment(avg_percent, class_position, class_size):
    score = float(avg_percent)
    pos_text = ''
    if class_position and class_size:
        pos_text = f" Position in class: {class_position} of {class_size}."
    if score >= 80:
        return (
            "The Head Teacher commends this learner for outstanding academic performance this term."
            + pos_text
            + " Maintain excellence and positive conduct."
        )
    if score >= 70:
        return (
            "The Head Teacher notes very good academic progress and encourages continued diligence."
            + pos_text
        )
    if score >= 60:
        return (
            "The Head Teacher acknowledges satisfactory progress and urges steady improvement in all areas."
            + pos_text
        )
    if score >= 50:
        return (
            "The Head Teacher advises improved study habits and closer follow-up with subject teachers."
            + pos_text
        )
    return (
        "The Head Teacher recommends intensive remedial support and parental involvement to raise achievement."
        + pos_text
    )


def compute_class_positions(students, term, academic_year, report_type):
    """Return dict student_id -> (position, class_size, avg)."""
    totals = {}
    for student in students:
        marks = MarkEntry.objects.filter(
            student=student,
            grading_term=term,
            academic_year=academic_year,
        ).select_related('subject', 'assessment_type')
        filtered = filter_marks_for_report(marks, report_type)
        rows = build_subject_rows(filtered)
        totals[student.id] = student_overall_average(rows)

    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    size = len(ranked)
    positions = {}
    for rank, (sid, avg) in enumerate(ranked, start=1):
        positions[sid] = (rank, size, avg)
    return positions


def build_student_report_data(student, term=None, academic_year=None, report_type=REPORT_END_TERM):
    term = term or student.school.active_term
    academic_year = academic_year or student.school.active_academic_year
    report_type = normalize_report_type(report_type)

    marks_qs = MarkEntry.objects.filter(
        student=student,
        grading_term=term,
        academic_year=academic_year,
    ).select_related('subject', 'assessment_type')
    filtered = filter_marks_for_report(marks_qs, report_type)
    subject_rows = build_subject_rows(filtered)
    overall_avg = student_overall_average(subject_rows)
    overall_grade = grade_from_score(float(overall_avg))

    classmates = Student.objects.filter(
        school=student.school,
        current_class=student.current_class,
        is_active=True,
    )
    positions = compute_class_positions(classmates, term, academic_year, report_type)
    class_position, class_size, _ = positions.get(student.id, (None, len(classmates), overall_avg))

    data = {
        'student': student,
        'school': student.school,
        'term': term,
        'academic_year': academic_year,
        'report_type': report_type,
        'report_title': report_type_label(report_type),
        'subjects': subject_rows,
        'overall_average': overall_avg,
        'overall_grade': overall_grade,
        'class_position': class_position,
        'class_size': class_size,
        'class_teacher_remark': class_teacher_comment(overall_avg),
        'head_teacher_remark': head_teacher_comment(overall_avg, class_position, class_size),
    }
    from .report_services import apply_term_record_to_report
    return apply_term_record_to_report(data)


def uganda_grade_distribution(marks_qs):
    """D1–F9 counts from mark entries."""
    counts = {g: 0 for g in ('D1', 'D2', 'C3', 'C4', 'C5', 'C6', 'P7', 'P8', 'F9')}
    for m in marks_qs:
        g = m.grade()
        counts[g] = counts.get(g, 0) + 1
    return counts


def analytics_chart_data(marks_qs):
    """JSON-serializable chart payloads for dashboards."""
    grade_counts = uganda_grade_distribution(marks_qs)
    labels = list(grade_counts.keys())
    values = [grade_counts[g] for g in labels]

    class_avgs = defaultdict(list)
    for m in marks_qs:
        class_avgs[m.student.current_class].append(float(m.score_achieved))

    class_labels = sorted(class_avgs.keys())
    class_values = [
        round(sum(class_avgs[c]) / len(class_avgs[c]), 1) if class_avgs[c] else 0
        for c in class_labels
    ]

    subject_avgs = defaultdict(list)
    for m in marks_qs:
        subject_avgs[m.subject.name].append(float(m.score_achieved))

    sub_sorted = sorted(subject_avgs.items(), key=lambda x: -sum(x[1]) / len(x[1]))[:8]
    subject_labels = [s[0] for s in sub_sorted]
    subject_values = [
        round(sum(s[1]) / len(s[1]), 1) if s[1] else 0 for s in sub_sorted
    ]

    scores = [float(m.score_achieved) for m in marks_qs]
    buckets = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '50-59': 0, 'Below 50': 0}
    for s in scores:
        if s >= 90:
            buckets['90-100'] += 1
        elif s >= 80:
            buckets['80-89'] += 1
        elif s >= 70:
            buckets['70-79'] += 1
        elif s >= 60:
            buckets['60-69'] += 1
        elif s >= 50:
            buckets['50-59'] += 1
        else:
            buckets['Below 50'] += 1

    return {
        'grade_labels': labels,
        'grade_values': values,
        'class_labels': class_labels,
        'class_values': class_values,
        'subject_labels': subject_labels,
        'subject_values': subject_values,
        'score_bucket_labels': list(buckets.keys()),
        'score_bucket_values': list(buckets.values()),
        'total_marks': len(scores),
        'average_score': round(sum(scores) / len(scores), 1) if scores else 0,
    }
