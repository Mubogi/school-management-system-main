from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
from django.db import models
from decimal import Decimal
from django.urls import reverse
from django.views.generic.base import RedirectView
from django.db.models import Q
from django.utils import timezone
from html import unescape
from io import BytesIO
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import re
import base64
import mimetypes
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from urllib.parse import urlparse, unquote
from pathlib import Path
from tempfile import NamedTemporaryFile
import os

from .models import (
    SchoolConfiguration, UserProfile, Student, StudentIDSequence, FeePaymentLedger, FeeStructure,
    MarkEntry, TeacherSubjectAssignment, ClassTeacherAssignment, SchoolClass, Subject,
    AssessmentType, FeeComponent, grade_from_score, PromotionCriteria, SchoolTermArchive,
)
from .forms import (
    StudentRegistrationForm, StudentEditForm, FeePaymentForm, FeeStructureForm, SchoolConfigForm, SchoolSettingsForm,
    StaffUserCreationForm, SchoolClassForm, SubjectForm, MarkEntryForm, AssessmentTypeForm,
    UserProfileEditForm, PromotionCriteriaForm, LoadNewTermForm,
)
from .student_utils import persist_student_from_form
from .fee_utils import (
    payment_context_for_receipt, resolve_fee_structure,
    record_payment_from_form, build_cleared_and_outstanding,
)
from .role_access import user_has_role, can_access_view
from .school_config_utils import can_edit_term_records, feature_enabled, is_term_locked
from .report_utils import (
    build_student_report_data, normalize_report_type, report_type_label,
    analytics_chart_data,
)
from django.contrib.auth.mixins import LoginRequiredMixin


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        profile = get_profile(request.user)
        if profile:
            if not profile.is_active:
                from django.contrib.auth import logout
                logout(request)
                return redirect('core:login')
            school = get_user_school(profile)
            if school and not school.is_active and profile.role != 'SUPER_ADMIN':
                from django.contrib.auth import logout
                from django.contrib import messages
                logout(request)
                messages.error(request, 'This school has been deactivated. Contact the system administrator.')
                return redirect('core:login')
            role_paths = {
                'SUPER_ADMIN': 'core:super_admin_dashboard',
                'SCHOOL_ADMIN': 'core:super_admin_dashboard',
                'SECRETARY': 'core:secretary_dashboard',
                'BURSAR': 'core:bursar_dashboard',
                'CLASS_TEACHER': 'core:class_teacher_dashboard',
                'SUBJECT_TEACHER': 'core:subject_teacher_dashboard',
                'DOS': 'core:dos_dashboard',
                'HEAD_TEACHER': 'core:head_teacher_dashboard',
            }
            redirect_path = role_paths.get(profile.role)
            if redirect_path:
                return redirect(redirect_path)
        return redirect('core:login')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['school'] = SchoolConfiguration.get_school()
        return ctx

try:
    import weasyprint
except Exception:
    weasyprint = None

try:
    from xhtml2pdf import pisa
except Exception:
    pisa = None


def get_profile(user):
    try:
        return user.userprofile
    except Exception:
        return None


def get_user_school(profile=None):
    """Return the single school for this deployment."""
    return SchoolConfiguration.get_school()


def require_role(profile, allowed_roles):
    if not user_has_role(profile, allowed_roles):
        raise Http404()


def student_belongs_to_school(student, school):
    return school and student.school_id == school.id


RECEIPT_ROLES = ['BURSAR', 'SECRETARY', 'SUPER_ADMIN', 'SCHOOL_ADMIN', 'HEAD_TEACHER']
BURSAR_PDF_ROLES = ['BURSAR', 'SUPER_ADMIN', 'SCHOOL_ADMIN']
BURSAR_LIST_PDF_ROLES = ['BURSAR', 'SUPER_ADMIN', 'SCHOOL_ADMIN', 'HEAD_TEACHER']
DEMAND_LETTER_ROLES = ['BURSAR', 'SECRETARY', 'SUPER_ADMIN', 'SCHOOL_ADMIN', 'HEAD_TEACHER']
CLEARANCE_PDF_ROLES = DEMAND_LETTER_ROLES
ACADEMIC_PDF_ROLES = [
    'SUPER_ADMIN', 'SCHOOL_ADMIN', 'HEAD_TEACHER', 'DOS', 'SECRETARY',
    'CLASS_TEACHER', 'SUBJECT_TEACHER',
]
ASSESSMENT_PDF_ROLES = ['SUPER_ADMIN', 'SCHOOL_ADMIN', 'SECRETARY', 'DOS', 'HEAD_TEACHER', 'CLASS_TEACHER', 'SUBJECT_TEACHER']
SUBJECT_PDF_ROLES = ASSESSMENT_PDF_ROLES


def can_view_receipt(profile, payment):
    if not profile:
        return False
    school = get_user_school(profile)
    if not student_belongs_to_school(payment.student, school):
        return False
    if profile.role in RECEIPT_ROLES:
        return True
    return can_view_student(profile, payment.student)


def image_file_uri(image_field):
    """Absolute file URI for WeasyPrint image embedding."""
    if not image_field:
        return ''
    try:
        from pathlib import Path
        path = Path(image_field.path)
        if path.exists():
            return path.as_uri()
    except Exception:
        pass
    return ''


def image_file_data_uri(image_field):
    """Embed local Django image fields as data URIs for Chromium rendering."""
    if not image_field:
        return ''
    try:
        path = image_field.path
        if not path or not os.path.exists(path):
            return ''
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or 'application/octet-stream'
        with open(path, 'rb') as f:
            data = f.read()
        return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
    except Exception:
        return ''


def create_watermark_bytes(school, width, height):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    c.saveState()
    try:
        c.setFillAlpha(0.08)
    except Exception:
        pass
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont('Helvetica-Bold', min(width, height) / 10)
    c.translate(width / 2, height / 2)
    c.rotate(45)
    if school and getattr(school, 'school_name', None):
        c.drawCentredString(0, 0, school.school_name)
    else:
        c.drawCentredString(0, 0, 'SCHOOL')
    if school and getattr(school, 'logo', None):
        try:
            logo_path = school.logo.path
            img = ImageReader(logo_path)
            img_width, img_height = img.getSize()
            max_dim = min(width, height) * 0.4
            scale = min(max_dim / img_width, max_dim / img_height)
            img_width *= scale
            img_height *= scale
            c.drawImage(
                img,
                -img_width / 2,
                -img_height / 2 - 100,
                width=img_width,
                height=img_height,
                preserveAspectRatio=True,
                mask='auto',
            )
        except Exception:
            pass
    c.restoreState()
    c.showPage()
    c.save()
    return buffer.getvalue()


def apply_pdf_watermark(pdf_bytes, school):
    # Watermarking has been disabled per user request.
    return pdf_bytes


def reportlab_pdf_from_html(html):
    text = html
    # remove <head> and <style> blocks entirely to avoid CSS text appearing
    text = re.sub(r'(?is)<head.*?>.*?</head>', '', text)
    text = re.sub(r'(?is)<style.*?>.*?</style>', '', text)
    # remove HTML comments and scripts
    text = re.sub(r'(?is)<!--.*?-->', '', text)
    text = re.sub(r'(?is)<script.*?>.*?</script>', '', text)
    # replace some closing tags with newlines
    text = re.sub(r'(?i)</p>|</div>|</h[1-6]>|<br\s*/?>', '\n', text)
    # strip any remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    buffer = BytesIO()
    page_width, page_height = 595.27, 841.89
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    x_margin = 40
    y = page_height - 40
    c.setFont('Helvetica', 10)
    for line in lines:
        if y < 40:
            c.showPage()
            c.setFont('Helvetica', 10)
            y = page_height - 40
        wrapped = []
        while len(line) > 100:
            split_at = line.rfind(' ', 0, 100)
            if split_at == -1:
                split_at = 100
            wrapped.append(line[:split_at])
            line = line[split_at:].strip()
        wrapped.append(line)
        for part in wrapped:
            c.drawString(x_margin, y, part)
            y -= 14
    c.save()
    return buffer.getvalue()


def render_html_chromium_bytes(html, base_url=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    base_tag = ''
    if base_url:
        safe_base_url = base_url.rstrip('/')
        base_tag = '<base href="%s/">' % safe_base_url
    full_html = '<!doctype html><html><head><meta charset="utf-8">%s</head><body>%s</body></html>' % (base_tag, html)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])
        try:
            page = browser.new_page()
            page.set_content(full_html, wait_until='networkidle', timeout=30000)
            page.emulate_media(media='print')
            pdf_bytes = page.pdf(format='A4', print_background=True, margin={'top': '16mm', 'bottom': '16mm', 'left': '16mm', 'right': '16mm'})
            page.close()
        finally:
            browser.close()
    return pdf_bytes


def generate_reportcard_reportlab_bytes(report):
    """Create a decorated report card PDF (bytes) using ReportLab Platypus.

    Expects `report` as the enriched dict returned by `enrich_report_for_pdf()`.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)

    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.fontName = 'Helvetica'
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1e40af'))
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=9, textColor=colors.grey)

    elems = []

    # Header: logo + school name + report title
    def _uri_to_path(uri):
        try:
            parsed = urlparse(uri)
            if parsed.scheme == 'file':
                p = unquote(parsed.path)
                # Windows file:// may have leading slash before drive letter
                if p.startswith('/') and len(p) > 2 and p[2] == ':' :
                    p = p[1:]
                return p
        except Exception:
            pass
        return uri

    logo = None
    try:
        if report.get('school_logo_uri'):
            logo_path = _uri_to_path(report['school_logo_uri'])
            logo = Image(logo_path, width=36*mm, height=36*mm)
        elif getattr(report.get('school'), 'logo', None):
            logo = Image(report['school'].logo.path, width=36*mm, height=36*mm)
    except Exception:
        logo = None

    school_name = report['school'].school_name if report.get('school') else 'School'
    report_title = f"{report.get('report_title', 'Report Card')} — {report.get('term', '')} / {report.get('academic_year', '')}"

    header_cells = []
    if logo:
        header_cells.append(logo)
    else:
        header_cells.append(Paragraph(f"<b>{school_name}</b>", title_style))
    header_cells.append(Paragraph(f"<b>{school_name}</b><br/><font size=10 color='#666666'>{report_title}</font>", normal))

    header_table = Table([[header_cells[0], header_cells[1]]], colWidths=[40*mm, None])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elems.append(header_table)
    elems.append(Spacer(1, 8))

    # Student info
    student = report.get('student')
    sid = student.student_id if student else 'N/A'
    student_name = f"{student.first_name} {student.last_name}" if student else 'Student'
    info_table = Table([
        ['Name:', student_name, 'ID:', sid],
        ['Class:', report.get('student').current_class if student else '', 'Rank:', f"{report.get('class_position','-')} / {report.get('class_size','-')}"]
    ], colWidths=[20*mm, None, 18*mm, 30*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('BOX', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
    ]))
    elems.append(info_table)
    elems.append(Spacer(1, 8))

    # Marks table
    marks = report.get('subjects', [])
    data = [['Subject', 'Details', 'Weighted', 'Grade']]
    for item in marks:
        details = '; '.join([f"{a['name']}: {a['score']}" for a in item.get('assessments', [])])
        data.append([item['subject'].name if item.get('subject') else '', details, str(item.get('weighted','')), item.get('grade','')])

    t = Table(data, colWidths=[70*mm, None, 24*mm, 24*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (2,1), (3,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fbfdff')]),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 10))

    # Stats badges
    badges = Table([
        [Paragraph('<b>Final Average</b><br/>' + str(report.get('overall_average','0.00'))+'%', normal),
         Paragraph('<b>Grade</b><br/>' + str(report.get('overall_grade','-')), normal),
         Paragraph('<b>Attendance</b><br/>' + f"{report.get('days_present','0')}/{report.get('total_school_days','0')}", normal)]
    ], colWidths=[None, None, None])
    badges.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elems.append(badges)
    elems.append(Spacer(1, 10))

    # Remarks
    elems.append(Paragraph('<b>Class Teacher\'s Remarks</b>', styles['Heading4']))
    elems.append(Paragraph(report.get('class_teacher_remark',''), normal))
    elems.append(Spacer(1,6))
    if report.get('dos_remark'):
        elems.append(Paragraph('<b>Director of Studies\'s Remarks</b>', styles['Heading4']))
        elems.append(Paragraph(report.get('dos_remark',''), normal))
        elems.append(Spacer(1,6))
    elems.append(Paragraph('<b>Head Teacher\'s Remarks</b>', styles['Heading4']))
    elems.append(Paragraph(report.get('head_teacher_remark',''), normal))
    elems.append(Spacer(1, 18))

    # Signatures
    sig_table = Table([['Class Teacher', '', 'Head Teacher', ''], ['', '', '', '']], colWidths=[60*mm, 10*mm, 60*mm, None])
    sig_table.setStyle(TableStyle([
        ('LINEABOVE', (0,1), (0,1), 0.5, colors.lightgrey),
        ('LINEABOVE', (2,1), (2,1), 0.5, colors.lightgrey),
    ]))
    elems.append(sig_table)

    # PDF watermark overlay removed per user request.
    doc.build(elems)
    return buf.getvalue()


def generate_reportcard_modern_bytes(report):
    """Modern styled report card using a contemporary palette and student avatar."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=16*mm, rightMargin=16*mm,
                            topMargin=16*mm, bottomMargin=16*mm)

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('normal_mod', parent=styles['Normal'], fontName='Helvetica', fontSize=10)
    header_title = ParagraphStyle('header_title', parent=styles['Heading1'], alignment=1, textColor=colors.white, fontSize=18)
    small = ParagraphStyle('small_mod', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6b7280'))

    # Modern palette (deep teal + coral)
    primary = colors.HexColor('#0f766e')
    accent = colors.HexColor('#fb7185')

    elems = []

    def _uri_to_path(uri):
        try:
            parsed = urlparse(uri)
            if parsed.scheme == 'file':
                p = unquote(parsed.path)
                if p.startswith('/') and len(p) > 2 and p[2] == ':' :
                    p = p[1:]
                return p
        except Exception:
            pass
        return uri

    school = report.get('school')
    school_name = school.school_name if school else 'School'
    report_title = f"{report.get('report_title','Report Card')} — {report.get('term','')} / {report.get('academic_year','')}"

    # Top colored banner with logo + title
    banner_left = []
    logo_img = None
    try:
        if report.get('school_logo_uri'):
            logo_img = Image(_uri_to_path(report['school_logo_uri']), width=28*mm, height=28*mm)
        elif getattr(school, 'logo', None):
            logo_img = Image(school.logo.path, width=28*mm, height=28*mm)
    except Exception:
        logo_img = None
    if logo_img:
        banner_left.append(logo_img)
    else:
        banner_left.append(Paragraph(school_name, ParagraphStyle('sname', parent=styles['Heading2'], textColor=colors.white)))

    banner = Table([[banner_left[0], Paragraph(f"<b>{school_name}</b><br/><font size=10 color='#ffffff'>{report_title}</font>", header_title)]], colWidths=[30*mm, None])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (0,0), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elems.append(banner)
    elems.append(Spacer(1, 6))

    # Student header row: avatar + info
    student = report.get('student')
    sid = student.student_id if student else 'N/A'
    student_name = f"{student.first_name} {student.last_name}" if student else 'Student'

    avatar = None
    try:
        if getattr(student, 'photo', None) and student.photo.path:
            avatar = Image(student.photo.path, width=32*mm, height=32*mm)
        elif report.get('student_photo_uri'):
            avatar = Image(_uri_to_path(report['student_photo_uri']), width=32*mm, height=32*mm)
    except Exception:
        avatar = None

    info = Table([
        [Paragraph(f"<b>{student_name}</b>", ParagraphStyle('sname2', parent=styles['Heading3'])), ''],
        [Paragraph(f"ID: <b>{sid}</b>", small), Paragraph(f"Class: <b>{report.get('class_name','-')}</b>", small)]
    ], colWidths=[None, 40*mm])
    info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))

    header_row = [[avatar or '', info]]
    hr = Table(header_row, colWidths=[34*mm, None])
    hr.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elems.append(hr)
    elems.append(Spacer(1, 8))

    # Marks table with cleaner modern styling
    marks = report.get('subjects', [])
    data = [[Paragraph('<b>Subject</b>', normal), Paragraph('<b>Score / Details</b>', normal), Paragraph('<b>Weighted</b>', normal), Paragraph('<b>Grade</b>', normal)]]
    for item in marks:
        details = '; '.join([f"{a['name']}: {a['score']}" for a in item.get('assessments', [])])
        data.append([item.get('subject').name if item.get('subject') else '', details, str(item.get('weighted','')), item.get('grade','')])

    t = Table(data, colWidths=[70*mm, None, 26*mm, 26*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (2,1), (3,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#e6eef0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fdfa')]),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 10))

    # Remarks and stats inline
    stats = Table([
        [Paragraph('<b>Average</b>', normal), Paragraph(str(report.get('overall_average','-')), normal), Paragraph('<b>Grade</b>', normal), Paragraph(str(report.get('overall_grade','-')), normal)]
    ], colWidths=[None, 24*mm, None, 24*mm])
    stats.setStyle(TableStyle([('ALIGN',(1,0),(1,0),'CENTER'), ('ALIGN',(3,0),(3,0),'CENTER')]))
    elems.append(stats)
    elems.append(Spacer(1, 8))

    elems.append(Paragraph('<b>Class Teacher\'s Remarks</b>', styles['Heading4']))
    elems.append(Paragraph(report.get('class_teacher_remark',''), normal))
    elems.append(Spacer(1,6))

    # Sign-off
    sig = Table([['Prepared by', '', 'Reviewed by', '']], colWidths=[None, 20*mm, None, 20*mm])
    sig.setStyle(TableStyle([('LINEABOVE', (0,1), (0,1), 0.5, colors.HexColor('#d1fae5')), ('LINEABOVE', (2,1), (2,1), 0.5, colors.HexColor('#d1fae5'))]))
    elems.append(Spacer(1, 18))
    elems.append(sig)

    # Watermark with logo if available
    def _watermark(canvas_obj, doc_obj):
        canvas_obj.saveState()
        try:
            canvas_obj.setFillAlpha(0.08)
        except Exception:
            pass
        canvas_obj.setFont('Helvetica-Bold', 60)
        canvas_obj.setFillColor(primary)
        canvas_obj.translate(A4[0]/2, A4[1]/2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, school_name.upper())
        # try draw logo centered faintly
        try:
            if report.get('school_logo_uri'):
                imgp = _uri_to_path(report['school_logo_uri'])
                img = ImageReader(imgp)
                iw, ih = img.getSize()
                maxd = min(A4[0], A4[1]) * 0.35
                scale = min(maxd/iw, maxd/ih)
                canvas_obj.drawImage(img, -iw*scale/2, -ih*scale/2 - 80, width=iw*scale, height=ih*scale, mask='auto')
        except Exception:
            pass
        canvas_obj.restoreState()

    doc.build(elems, onFirstPage=_watermark, onLaterPages=_watermark)
    return buf.getvalue()


def render_html_chromium_bytes(html, base_url=None):
    """Render arbitrary HTML to PDF bytes using Playwright Chromium."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError('Playwright is not installed') from e

    base_tag = ''
    if base_url:
        safe_base_url = base_url.rstrip('/')
        base_tag = '<base href="%s/">' % safe_base_url
    full_html = '<!doctype html><html><head><meta charset="utf-8">%s</head><body>%s</body></html>' % (base_tag, html)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])
        try:
            page = browser.new_page()
            page.set_content(full_html, wait_until='networkidle', timeout=30000)
            page.emulate_media(media='print')
            pdf_bytes = page.pdf(format='A4', print_background=True, margin={'top': '16mm', 'bottom': '16mm', 'left': '16mm', 'right': '16mm'})
            page.close()
        finally:
            browser.close()
    return pdf_bytes


def generate_reportcard_chromium_bytes(report):
    """Render the HTML report fragment with headless Chromium (Playwright) and return PDF bytes."""
    try:
        html = render_to_string('core/pdf/report_card_fragment.html', {'report': report})
    except Exception:
        html = f"<html><body><pre>{str(report)}</pre></body></html>"
    from django.conf import settings
    return render_html_chromium_bytes(html, base_url=str(settings.BASE_DIR))


def role_required(allowed_roles):
    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            profile = get_profile(request.user)
            if not user_has_role(profile, allowed_roles):
                raise Http404()
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def can_view_student(profile, student):
    if not profile:
        return False
    school = get_user_school(profile)
    if not student_belongs_to_school(student, school):
        return False
    if profile.role in ['SUPER_ADMIN', 'SCHOOL_ADMIN', 'SECRETARY', 'BURSAR', 'DOS', 'HEAD_TEACHER']:
        return True
    if profile.role == 'CLASS_TEACHER':
        return TeacherSubjectAssignment.objects.filter(teacher=profile, assigned_class=student.current_class).exists() or \
            ClassTeacherAssignment.objects.filter(teacher=profile, school_class__name=student.current_class).exists()
    if profile.role == 'SUBJECT_TEACHER':
        return TeacherSubjectAssignment.objects.filter(teacher=profile, assigned_class=student.current_class).exists()
    return False


def teacher_can_enter_mark(profile, student=None, subject=None):
    if not profile:
        return False
    if profile.role in ['SUPER_ADMIN', 'SCHOOL_ADMIN', 'SECRETARY', 'DOS', 'HEAD_TEACHER']:
        return True
    if profile.role == 'CLASS_TEACHER':
        return True
    if profile.role == 'SUBJECT_TEACHER':
        return True
    return False


def marks_page_context(profile, *, restrict_class=None, restrict_subject_ids=None):
    """Shared context for marks management pages."""
    school = get_user_school(profile)
    if not school:
        return {}

    term = school.active_term
    year = school.active_academic_year
    subjects_qs = Subject.objects.filter(school=school)
    students_qs = Student.objects.filter(school=school, is_active=True)

    if restrict_class:
        subjects_qs = subjects_qs.filter(class_level=restrict_class)
        students_qs = students_qs.filter(current_class=restrict_class)
    if restrict_subject_ids:
        subjects_qs = subjects_qs.filter(pk__in=restrict_subject_ids)
        class_names = subjects_qs.values_list('class_level', flat=True).distinct()
        students_qs = students_qs.filter(current_class__in=class_names)

    marks_qs = MarkEntry.objects.filter(
        student__school=school,
        grading_term=term,
        academic_year=year,
    ).select_related('student', 'subject', 'assessment_type', 'recorded_by__user')

    if restrict_class:
        marks_qs = marks_qs.filter(student__current_class=restrict_class)
    if restrict_subject_ids:
        marks_qs = marks_qs.filter(subject_id__in=restrict_subject_ids)

    scores = [float(m.score_achieved) for m in marks_qs]
    ctx = {
        'classes': SchoolClass.objects.filter(school=school),
        'subjects': subjects_qs.order_by('name'),
        'assessments': AssessmentType.objects.filter(school=school),
        'students': students_qs.order_by('last_name', 'first_name'),
        'recent_marks': marks_qs.order_by('-recorded_at')[:500],
        'total_marks_count': len(scores),
        'average_score': round(sum(scores) / len(scores), 1) if scores else 'N/A',
        'highest_score': max(scores) if scores else 'N/A',
        'lowest_score': min(scores) if scores else 'N/A',
        'grade_a_count': sum(1 for s in scores if s >= 80),
        'grade_b_count': sum(1 for s in scores if 70 <= s < 80),
        'grade_c_count': sum(1 for s in scores if 60 <= s < 70),
        'grade_d_count': sum(1 for s in scores if s < 60),
        'chart_data': analytics_chart_data(marks_qs),
    }
    return ctx


def build_student_balances(school):
    balances = []
    total_outstanding = Decimal('0.00')
    for student in Student.objects.filter(school=school, is_active=True).order_by('current_class', 'last_name'):
        balance = student.balance()
        if balance is not None and balance > Decimal('0.00'):
            balances.append({
                'student': student,
                'balance': balance,
                'total_required': student.total_fees_required(),
                'total_paid': student.total_paid(),
            })
            total_outstanding += balance
    return balances, total_outstanding


def build_dos_class_summary(school):
    """Class list with student counts and detail links for DOS pages."""
    from django.urls import reverse
    summary = []
    for school_class in SchoolClass.objects.filter(school=school):
        count = Student.objects.filter(school=school, current_class=school_class.name, is_active=True).count()
        summary.append({
            'class_name': school_class.name,
            'student_count': count,
            'detail_url': reverse('core:dos_students') + f'?class={school_class.name}',
            'broadsheet_url': reverse('core:class_broadsheet_pdf', args=[school_class.name]),
        })
    return summary


def pdf_base_context(school):
    """Shared letterhead + footer context for PDF templates."""
    return {
        'school': school,
        'school_logo_uri': image_file_uri(school.logo) if school else '',
    }


def score_letter_band(score):
    if score >= 80:
        return 'A'
    if score >= 70:
        return 'B'
    if score >= 60:
        return 'C'
    if score >= 50:
        return 'D'
    return 'E'


def render_pdf_response(html, filename, school=None):
    pdf_bytes = None
    try:
        pdf_bytes = render_html_chromium_bytes(html, base_url=str(settings.BASE_DIR))
    except Exception:
        pdf_bytes = None
    if pdf_bytes is None and weasyprint:
        try:
            base_url = str(settings.BASE_DIR)
            pdf_bytes = weasyprint.HTML(string=html, base_url=base_url).write_pdf()
        except Exception:
            pdf_bytes = None
    if pdf_bytes is None and pisa:
        result = BytesIO()
        if pisa.CreatePDF(html, dest=result, encoding='utf-8').err:
            pdf_bytes = None
        else:
            pdf_bytes = result.getvalue()
    if pdf_bytes is None:
        try:
            pdf_bytes = reportlab_pdf_from_html(html)
        except Exception:
            pdf_bytes = None
    if not pdf_bytes:
        return HttpResponse(
            'PDF generation failed. Install Playwright/Chromium, ReportLab, WeasyPrint (GTK on Windows), or xhtml2pdf.',
            status=500,
        )
    if school is not None:
        pdf_bytes = apply_pdf_watermark(pdf_bytes, school)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def pdf_school_for_user(profile):
    """School used for PDF generation — prefers the user's assigned school."""
    return get_user_school(profile) or SchoolConfiguration.get_active()


def enrich_report_for_pdf(report_data):
    """Add image URIs for logos and photos so HTML renderers can embed them."""
    school = report_data.get('school')
    student = report_data.get('student')
    report_data['school_logo_uri'] = image_file_data_uri(school.logo) or image_file_uri(school.logo) if school else ''
    report_data['student_photo_uri'] = image_file_data_uri(student.passport_photo) or image_file_uri(student.passport_photo) if student else ''
    return report_data


def build_academic_reports_context(school):
    """Shared analytics context for HM/DOS academic report pages."""
    term = school.active_term
    academic_year = school.active_academic_year
    students = Student.objects.filter(school=school, is_active=True)
    marks = MarkEntry.objects.filter(
        student__in=students,
        grading_term=term,
        academic_year=academic_year,
    ).select_related('student', 'subject')

    class_totals = {}
    subject_totals = {}
    subject_class_totals = {}
    overall_totals = {}

    for mark in marks:
        student_obj = mark.student
        class_name = student_obj.current_class
        subject = mark.subject
        weighted = mark.weighted_score()

        class_entry = class_totals.setdefault(class_name, {})
        student_entry = class_entry.setdefault(
            student_obj.id, {'student': student_obj, 'total': Decimal('0.00')}
        )
        student_entry['total'] += weighted

        subject_entry = subject_totals.setdefault(subject.id, {'subject': subject, 'students': {}})
        subject_student_entry = subject_entry['students'].setdefault(
            student_obj.id, {'student': student_obj, 'total': Decimal('0.00')}
        )
        subject_student_entry['total'] += weighted

        sc_key = (class_name, subject.id)
        sc_entry = subject_class_totals.setdefault(
            sc_key, {'class_name': class_name, 'subject': subject, 'students': {}}
        )
        sc_student_entry = sc_entry['students'].setdefault(
            student_obj.id, {'student': student_obj, 'total': Decimal('0.00')}
        )
        sc_student_entry['total'] += weighted

        if student_obj.id not in overall_totals:
            overall_totals[student_obj.id] = {'student': student_obj, 'total': Decimal('0.00')}
        overall_totals[student_obj.id]['total'] += weighted

    top_students_by_class = []
    for class_name, students_map in class_totals.items():
        best_student = max(students_map.values(), key=lambda item: item['total'])
        top_students_by_class.append({
            'class_name': class_name,
            'student': best_student['student'],
            'total': best_student['total'],
            'grade': grade_from_score(float(best_student['total'])),
        })

    best_students_by_subject = []
    for subject_entry in subject_totals.values():
        best_student = max(subject_entry['students'].values(), key=lambda item: item['total'])
        best_students_by_subject.append({
            'subject': subject_entry['subject'],
            'student': best_student['student'],
            'total': best_student['total'],
            'grade': grade_from_score(float(best_student['total'])),
        })

    best_students_by_subject_in_class = []
    for sc_entry in subject_class_totals.values():
        if not sc_entry['students']:
            continue
        best_student = max(sc_entry['students'].values(), key=lambda item: item['total'])
        best_students_by_subject_in_class.append({
            'class_name': sc_entry['class_name'],
            'subject': sc_entry['subject'],
            'student': best_student['student'],
            'total': best_student['total'],
            'grade': grade_from_score(float(best_student['total'])),
        })

    top_students_overall = sorted(
        [
            {
                'student': data['student'],
                'total': data['total'],
                'grade': grade_from_score(float(data['total'])),
            }
            for data in overall_totals.values()
        ],
        key=lambda item: item['total'],
        reverse=True,
    )[:10]

    return {
        'classes': SchoolClass.objects.filter(school=school),
        'chart_data': analytics_chart_data(marks),
        'top_students_by_class': top_students_by_class,
        'best_students_by_subject': best_students_by_subject,
        'best_students_by_subject_in_class': best_students_by_subject_in_class,
        'top_students_overall': top_students_overall,
    }


class RoleRequiredMixin:
    allowed_roles = []

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        if not can_access_view(profile, self.allowed_roles):
            raise Http404()
        school = get_user_school(profile)
        if school and not school.is_active and profile.role != 'SUPER_ADMIN':
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


class SuperAdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/super_admin.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        ctx['school'] = school
        ctx['selected_school'] = school
        ctx['school_form'] = SchoolConfigForm()
        ctx['staff_form'] = StaffUserCreationForm(school=school)
        ctx['student_form'] = StudentRegistrationForm(school=school)
        ctx['class_form'] = SchoolClassForm()
        ctx['subject_form'] = SubjectForm()

        if school:
            ctx['assessment_types'] = AssessmentType.objects.filter(school=school)
            ctx['fee_structures'] = FeeStructure.objects.filter(school=school).order_by('target_class', 'term')
            ctx['staff_users'] = UserProfile.objects.filter(school=school).select_related('user')
            ctx['students'] = Student.objects.filter(school=school).order_by('-enrollment_date')[:30]
            ctx['classes'] = SchoolClass.objects.filter(school=school)
            ctx['subjects'] = Subject.objects.filter(school=school)
            ctx['class_teacher_assignments'] = ClassTeacherAssignment.objects.filter(school_class__school=school).select_related('teacher', 'school_class')
            ctx['subject_assignments'] = TeacherSubjectAssignment.objects.filter(subject__school=school).select_related('teacher', 'subject')
            ctx['fee_components'] = FeeComponent.objects.filter(fee_structure__school=school).select_related('fee_structure')
            seq, _ = StudentIDSequence.objects.get_or_create(school=school)
            next_number = seq.last_number + 1
            ctx['next_student_id'] = f"{school.school_initials_prefix}-{str(next_number).zfill(5)}"
            criteria, _ = PromotionCriteria.objects.get_or_create(school=school)
            ctx['promotion_criteria_form'] = PromotionCriteriaForm(instance=criteria)
            ctx['load_term_form'] = LoadNewTermForm(initial={
                'new_term': school.active_term,
                'new_academic_year': school.active_academic_year,
            })
            ctx['term_archives'] = SchoolTermArchive.objects.filter(school=school)[:10]
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()

        if action == 'save_promotion_criteria':
            criteria, _ = PromotionCriteria.objects.get_or_create(school=school)
            form = PromotionCriteriaForm(request.POST, instance=criteria)
            if form.is_valid():
                form.save()
            return redirect('core:super_admin_dashboard')
        elif action == 'load_new_term':
            form = LoadNewTermForm(request.POST)
            if form.is_valid():
                SchoolTermArchive.objects.get_or_create(
                    school=school,
                    term=school.active_term,
                    academic_year=school.active_academic_year,
                    defaults={
                        'reports_published': form.cleaned_data.get('reports_were_published', False),
                        'notes': form.cleaned_data.get('archive_notes', ''),
                        'closed_by': profile,
                    },
                )
                school.active_term = form.cleaned_data['new_term']
                school.active_academic_year = form.cleaned_data['new_academic_year']
                school.fees_demanded = False
                school.term_open_for_academics = False
                school.save()
            return redirect('core:super_admin_dashboard')
        elif action == 'create_assessment':
            name = request.POST.get('assessment_name')
            weight = request.POST.get('assessment_weight')
            if name and weight:
                try:
                    AssessmentType.objects.create(school=school, name=name, weight_percentage=Decimal(weight))
                except Exception:
                    pass
            return redirect('core:super_admin_dashboard')
        elif action == 'create_fee':
            target_class = request.POST.get('target_class')
            school_class_id = request.POST.get('school_class_id')
            term = request.POST.get('term')
            academic_year = request.POST.get('academic_year')
            total_fees = request.POST.get('total_fees')
            school_class = SchoolClass.objects.filter(pk=school_class_id, school=school).first() if school_class_id else None
            if all([target_class, term, academic_year, total_fees]):
                try:
                    FeeStructure.objects.create(
                        school=school,
                        school_class=school_class,
                        target_class=target_class,
                        term=term,
                        academic_year=academic_year,
                        total_fees_required=Decimal(total_fees)
                    )
                except Exception:
                    pass
            return redirect('core:super_admin_dashboard')
        elif action == 'create_class':
            class_form = SchoolClassForm(request.POST)
            if class_form.is_valid():
                school_class = class_form.save(commit=False)
                school_class.school = school
                school_class.save()
            return redirect('core:super_admin_dashboard')
        elif action == 'create_subject':
            subject_form = SubjectForm(request.POST)
            if subject_form.is_valid():
                subject = subject_form.save(commit=False)
                subject.school = school
                subject.save()
            return redirect('core:super_admin_dashboard')
        elif action == 'assign_class_teacher':
            teacher_id = request.POST.get('class_teacher_id')
            school_class_id = request.POST.get('class_assignment_id')
            teacher = UserProfile.objects.filter(
                pk=teacher_id, school=school,
                role__in=['CLASS_TEACHER', 'DOS', 'HEAD_TEACHER'],
            ).first()
            school_class = SchoolClass.objects.filter(pk=school_class_id, school=school).first()
            if teacher and school_class:
                ClassTeacherAssignment.objects.get_or_create(teacher=teacher, school_class=school_class)
            return redirect('core:super_admin_dashboard')
        elif action == 'assign_subject_teacher':
            teacher_id = request.POST.get('subject_teacher_id')
            subject_id = request.POST.get('subject_assignment_id')
            class_id = request.POST.get('subject_class_id')
            teacher = UserProfile.objects.filter(
                pk=teacher_id, school=school,
                role__in=['SUBJECT_TEACHER', 'CLASS_TEACHER', 'DOS', 'HEAD_TEACHER'],
            ).first()
            subject = Subject.objects.filter(pk=subject_id, school=school).first()
            school_class = SchoolClass.objects.filter(pk=class_id, school=school).first()
            if teacher and subject and school_class:
                TeacherSubjectAssignment.objects.create(
                    teacher=teacher,
                    subject=subject,
                    assigned_class=school_class.name
                )
            return redirect('core:super_admin_dashboard')
        elif action == 'create_fee_component':
            fee_structure_id = request.POST.get('fee_structure_id')
            name = request.POST.get('fee_component_name')
            amount = request.POST.get('fee_component_amount')
            fee_structure = FeeStructure.objects.filter(pk=fee_structure_id, school=school).first()
            if fee_structure and name and amount:
                try:
                    FeeComponent.objects.create(
                        fee_structure=fee_structure,
                        name=name,
                        amount=Decimal(amount)
                    )
                except Exception:
                    pass
            return redirect('core:super_admin_dashboard')
        elif action == 'create_user':
            staff_form = StaffUserCreationForm(request.POST, school=school)
            if staff_form.is_valid():
                user = get_user_model().objects.create_user(
                    username=staff_form.cleaned_data['username'],
                    email=staff_form.cleaned_data['email'],
                    password=staff_form.cleaned_data['password'],
                    first_name=staff_form.cleaned_data['first_name'],
                    last_name=staff_form.cleaned_data['last_name'],
                )
                user_profile = UserProfile.objects.create(
                    user=user,
                    role=staff_form.cleaned_data['role'],
                    school=school,
                )
                assigned_class = staff_form.cleaned_data.get('assigned_class')
                if assigned_class and staff_form.cleaned_data['role'] in ['CLASS_TEACHER', 'DOS', 'HEAD_TEACHER']:
                    ClassTeacherAssignment.objects.get_or_create(
                        teacher=user_profile, school_class=assigned_class
                    )
                if staff_form.cleaned_data['role'] in ['CLASS_TEACHER', 'SUBJECT_TEACHER', 'DOS', 'HEAD_TEACHER']:
                    for subject in staff_form.cleaned_data.get('assigned_subjects', []):
                        TeacherSubjectAssignment.objects.get_or_create(
                            teacher=user_profile,
                            subject=subject,
                            assigned_class=subject.class_level,
                        )
                return redirect('core:super_admin_dashboard')
            ctx = self.get_context_data(**kwargs)
            ctx['staff_form'] = staff_form
            return render(request, self.template_name, ctx)
        elif action == 'create_student':
            student_form = StudentRegistrationForm(request.POST, request.FILES, school=school)
            if student_form.is_valid():
                persist_student_from_form(student_form, school)
                return redirect('core:super_admin_dashboard')
            ctx = self.get_context_data(**kwargs)
            ctx['student_form'] = student_form
            return render(request, self.template_name, ctx)
        return self.get(request, *args, **kwargs)


class SecretaryDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/secretary.html'
    allowed_roles = ['SECRETARY']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        ctx['school'] = get_user_school(profile)
        school = get_user_school(profile)
        ctx['form'] = StudentRegistrationForm(school=school)
        if school:
            ctx['students'] = Student.objects.filter(school=school).order_by('-enrollment_date')[:50]
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        form = StudentRegistrationForm(request.POST, request.FILES, school=school)
        if form.is_valid() and school:
            persist_student_from_form(form, school)
            return redirect('core:secretary_dashboard')
        ctx = self.get_context_data()
        ctx['form'] = form
        return render(request, self.template_name, ctx)


class BursarDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/bursar.html'
    allowed_roles = ['BURSAR']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        ctx['school'] = get_user_school(profile)
        school = get_user_school(profile)
        ctx['form'] = FeePaymentForm(school=school)
        if school:
            ctx['payments'] = FeePaymentLedger.objects.filter(student__school=school).order_by('-date_of_payment')[:50]
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        form = FeePaymentForm(request.POST, school=get_user_school(profile))
        payment, form = record_payment_from_form(request, form, profile)
        if payment:
            return redirect(reverse('core:receipt_view', args=[payment.unique_receipt_id]))
        ctx = self.get_context_data(**kwargs)
        ctx['form'] = form
        return render(request, self.template_name, ctx)


class SubjectTeacherDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/subject_teacher.html'
    allowed_roles = ['SUBJECT_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        ctx['school'] = get_user_school(profile)
        assignments = TeacherSubjectAssignment.objects.filter(teacher=profile)
        ctx['assignments'] = assignments
        return ctx


class ClassTeacherDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/class_teacher.html'
    allowed_roles = ['CLASS_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        ctx['school'] = get_user_school(profile)
        # assume profile has an attribute or assignment describing their class; for simplicity look up assignments
        school = get_user_school(profile)
        assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
        if assignment and school:
            ctx['assigned_class'] = assignment.school_class
            ctx['students'] = Student.objects.filter(school=school, current_class=assignment.school_class.name)
        return ctx


class DOSDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/dos.html'
    allowed_roles = ['DOS']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        school = get_user_school(profile)
        ctx['school'] = school
        ctx['class_performance'] = []
        if school:
            ctx['total_students'] = Student.objects.filter(school=school, is_active=True).count()
            ctx['total_classes'] = SchoolClass.objects.filter(school=school).count()
            ctx['total_subjects'] = Subject.objects.filter(school=school).count()
            marks_qs = MarkEntry.objects.filter(
                student__school=school,
                grading_term=school.active_term,
                academic_year=school.active_academic_year,
            )
            ctx['marks_recorded'] = marks_qs.count()
            avg = marks_qs.aggregate(avg=models.Avg('score_achieved'))['avg']
            ctx['average_performance'] = round(avg, 1) if avg else 0
            academic = build_academic_reports_context(school)
            ctx['chart_data'] = academic.get('chart_data')
            for row in academic.get('top_students_by_class', []):
                ctx['class_performance'].append({
                    'class_name': row['class_name'],
                    'average': row['total'],
                    'top_student': row['student'],
                })
        return ctx


class HeadTeacherDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dashboards/head_teacher.html'
    allowed_roles = ['HEAD_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['current_date'] = timezone.now().strftime('%A, %B %d, %Y')
        school = get_user_school(profile)
        ctx['school'] = school
        if school:
            ctx['total_students'] = Student.objects.filter(school=school).count()
            ctx['total_classes'] = SchoolClass.objects.filter(school=school).count()
            ctx['total_staff'] = UserProfile.objects.filter(school=school).exclude(role='SUPER_ADMIN').count()
            ctx['total_subjects'] = Subject.objects.filter(school=school).count()
            marks_qs = MarkEntry.objects.filter(student__school=school, grading_term=school.active_term, academic_year=school.active_academic_year)
            ctx['marks_recorded'] = marks_qs.count()
            avg_score = marks_qs.aggregate(avg=models.Avg('score_achieved'))['avg']
            ctx['average_performance'] = round(avg_score, 2) if avg_score else 0
        return ctx


@login_required
def receipt_view(request, receipt_id):
    profile = get_profile(request.user)
    payment = get_object_or_404(FeePaymentLedger, unique_receipt_id=receipt_id)
    if not can_view_receipt(profile, payment):
        raise Http404()
    context = {'payment': payment, **payment_context_for_receipt(payment)}
    return render(request, 'core/receipt.html', context)


@login_required
def mark_entry_view(request):
    profile = get_profile(request.user)
    allowed_roles = ['SUBJECT_TEACHER', 'CLASS_TEACHER', 'SECRETARY', 'DOS', 'HEAD_TEACHER', 'SUPER_ADMIN', 'SCHOOL_ADMIN']
    if not user_has_role(profile, allowed_roles):
        raise Http404()

    if request.method == 'POST':
        school = get_user_school(profile)
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        assessment_id = request.POST.get('assessment_id')
        score = request.POST.get('score')
        student = get_object_or_404(Student, student_id=student_id, school=school)
        subject = get_object_or_404(Subject, pk=subject_id, school=school)
        assessment = get_object_or_404(AssessmentType, pk=assessment_id, school=school)

        if profile.role in ['SUBJECT_TEACHER', 'CLASS_TEACHER']:
            allowed = TeacherSubjectAssignment.objects.filter(
                teacher=profile, subject=subject, assigned_class=student.current_class
            ).exists()
            if profile.role == 'CLASS_TEACHER' and not allowed:
                allowed = ClassTeacherAssignment.objects.filter(
                    teacher=profile, school_class__name=student.current_class
                ).exists()
            if not allowed:
                raise Http404()

        if school and not school.term_open_for_academics and profile.role in ['SECRETARY', 'CLASS_TEACHER', 'SUBJECT_TEACHER']:
            next_url = request.POST.get('next') or reverse('core:home')
            return redirect(next_url)

        if school and not can_edit_term_records(profile, school):
            next_url = request.POST.get('next') or reverse('core:home')
            from django.contrib import messages
            messages.error(request, 'This term is closed. Records cannot be edited.')
            return redirect(next_url)

        if school and not feature_enabled(school, 'marks_entry') and profile.role != 'SUPER_ADMIN':
            next_url = request.POST.get('next') or reverse('core:home')
            return redirect(next_url)

        MarkEntry.objects.update_or_create(
            student=student,
            subject=subject,
            assessment_type=assessment,
            grading_term=student.school.active_term,
            academic_year=student.school.active_academic_year,
            defaults={
                'score_achieved': Decimal(score),
                'recorded_by': profile,
            },
        )
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return HttpResponse('OK')

    raise Http404()


@login_required
def student_report_pdf(request, student_id, report_type=None, term=None, academic_year=None):
    profile = get_profile(request.user)
    student = get_object_or_404(Student, student_id=student_id)
    if not can_view_student(profile, student):
        raise Http404()

    term = term or student.school.active_term
    academic_year = academic_year or student.school.active_academic_year
    report_type = normalize_report_type(report_type or 'eot')

    report = enrich_report_for_pdf(
        build_student_report_data(student, term, academic_year, report_type)
    )
    report['generated_at'] = timezone.now()
    normalized = normalize_report_type(report_type)
    filename = f'{student.student_id}_report_{normalized}_{academic_year}_{term}.pdf'
    html = render_to_string('core/pdf/report_card_fragment.html', {'report': report})
    return render_pdf_response(html, filename, school=student.school)


@login_required
def receipt_pdf(request, receipt_id):
    profile = get_profile(request.user)
    payment = get_object_or_404(FeePaymentLedger, unique_receipt_id=receipt_id)
    if not can_view_receipt(profile, payment):
        raise Http404()
    school = get_user_school(profile)
    context = {
        **pdf_base_context(school),
        'payment': payment,
        **payment_context_for_receipt(payment),
    }
    html = render_to_string('core/pdf/receipt.html', context)
    return render_pdf_response(html, f'receipt_{receipt_id}.pdf', school=school)


@login_required
def student_financial_statement_pdf(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    if not can_view_student(get_profile(request.user), student):
        raise Http404()

    school = student.school
    term = school.active_term
    academic_year = school.active_academic_year
    fee_struct, _ = resolve_fee_structure(school, student.current_class, term, academic_year)
    total_required = fee_struct.compute_total() if fee_struct else Decimal('0.00')
    payments = FeePaymentLedger.objects.filter(
        student=student, term=term, academic_year=academic_year
    ).order_by('date_of_payment')
    if not payments.exists():
        payments = FeePaymentLedger.objects.filter(student=student).order_by('date_of_payment')
    total_paid = payments.aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0.00')
    balance = student.balance(term, academic_year)
    fee_items = fee_struct.fee_items() if fee_struct else []

    fee_breakdown = []
    for fs in student.get_all_fee_structures(term, academic_year):
        ft = fs.fee_type or 'General'
        fee_breakdown.append({
            'fee_type': ft,
            'required': fs.compute_total(),
            'paid': student.total_paid(term, academic_year, fee_type=ft),
            'balance': student.balance(term, academic_year, fee_type=ft),
        })

    context = {
        **pdf_base_context(school),
        'student': student,
        'term': term,
        'academic_year': academic_year,
        'total_required': total_required,
        'total_paid': total_paid,
        'balance': balance,
        'fee_items': fee_items,
        'fee_breakdown': fee_breakdown,
        'payments': payments,
    }
    html = render_to_string('core/pdf/financial_statement.html', context)
    return render_pdf_response(html, f'{student.student_id}_financial_statement.pdf', school=school)


@login_required
def bursar_demand_letter_pdf(request, student_id):
    profile = get_profile(request.user)
    require_role(profile, DEMAND_LETTER_ROLES)
    school = get_user_school(profile)
    student = get_object_or_404(Student, student_id=student_id, school=school)
    balance = student.balance() or Decimal('0.00')
    context = {
        **pdf_base_context(student.school),
        'student': student,
        'balance': balance,
        'term': student.school.active_term,
        'academic_year': student.school.active_academic_year,
        'total_required': student.total_fees_required(),
        'total_paid': student.total_paid(),
    }
    html = render_to_string('core/pdf/bursar_demand_letter.html', context)
    return render_pdf_response(html, f'demand_{student.student_id}.pdf', school=school)


@login_required
def bursar_fee_report_pdf(request):
    profile = get_profile(request.user)
    require_role(profile, BURSAR_PDF_ROLES)
    school = get_user_school(profile)
    balances, total_outstanding = build_student_balances(school)
    cleared, outstanding = build_cleared_and_outstanding(school)
    context = {
        **pdf_base_context(school),
        'balances': balances,
        'outstanding': outstanding,
        'cleared': cleared,
        'total_outstanding': total_outstanding,
        'term': school.active_term,
        'academic_year': school.active_academic_year,
    }
    html = render_to_string('core/pdf/bursar_fee_report.html', context)
    return render_pdf_response(html, f'fee_report_{school.active_term}.pdf', school=school)


@login_required
def bursar_clearance_list_pdf(request):
    profile = get_profile(request.user)
    require_role(profile, BURSAR_LIST_PDF_ROLES)
    school = get_user_school(profile)
    cleared, _ = build_cleared_and_outstanding(school)
    context = {
        **pdf_base_context(school),
        'cleared': cleared,
        'term': school.active_term,
        'academic_year': school.active_academic_year,
    }
    html = render_to_string('core/pdf/fee_clearance_list.html', context)
    return render_pdf_response(html, f'cleared_students_{school.active_term}.pdf', school=school)


@login_required
def bursar_outstanding_list_pdf(request):
    profile = get_profile(request.user)
    require_role(profile, BURSAR_PDF_ROLES)
    school = get_user_school(profile)
    _, outstanding = build_cleared_and_outstanding(school)
    context = {
        **pdf_base_context(school),
        'outstanding': outstanding,
        'total_outstanding': sum((e['balance'] for e in outstanding), Decimal('0.00')),
        'term': school.active_term,
        'academic_year': school.active_academic_year,
    }
    html = render_to_string('core/pdf/fee_outstanding_list.html', context)
    return render_pdf_response(html, f'outstanding_students_{school.active_term}.pdf', school=school)


@login_required
def student_clearance_pdf(request, student_id):
    profile = get_profile(request.user)
    require_role(profile, CLEARANCE_PDF_ROLES)
    school = get_user_school(profile)
    student = get_object_or_404(Student, student_id=student_id, school=school)
    if not student.is_fees_cleared():
        return HttpResponse('Student still has an outstanding balance.', status=400)
    context = {
        **pdf_base_context(student.school),
        'student': student,
        'term': student.school.active_term,
        'academic_year': student.school.active_academic_year,
        'total_paid': student.total_paid(),
        'total_required': student.total_fees_required(),
    }
    html = render_to_string('core/pdf/fee_clearance_certificate.html', context)
    return render_pdf_response(html, f'clearance_{student.student_id}.pdf', school=student.school)


@login_required
def assessment_report_pdf(request, assessment_id, term=None, academic_year=None):
    profile = get_profile(request.user)
    require_role(profile, ASSESSMENT_PDF_ROLES)
    school = get_user_school(profile)
    assessment = get_object_or_404(AssessmentType, pk=assessment_id, school=school)

    term = term or school.active_term
    academic_year = academic_year or school.active_academic_year
    entries = MarkEntry.objects.filter(
        assessment_type=assessment,
        grading_term=term,
        academic_year=academic_year,
    ).select_related('student', 'subject').order_by('student__current_class', 'subject__name', 'student__last_name')

    scores = [float(e.score_achieved) for e in entries]
    grade_distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
    for score in scores:
        grade_distribution[score_letter_band(score)] += 1

    data_by_class = {}
    for entry in entries:
        class_name = entry.student.current_class
        subject_name = entry.subject.name
        data_by_class.setdefault(class_name, {})
        data_by_class[class_name].setdefault(subject_name, [])
        data_by_class[class_name][subject_name].append(entry)

    stats = {
        'total_marks': len(scores),
        'average_score': round(sum(scores) / len(scores), 1) if scores else 0,
        'highest_score': max(scores) if scores else 0,
        'lowest_score': min(scores) if scores else 0,
        'grade_distribution': grade_distribution,
    }

    context = {
        **pdf_base_context(school),
        'assessment': assessment,
        'term': term,
        'academic_year': academic_year,
        'stats': stats,
        'data_by_class': data_by_class,
    }
    html = render_to_string('core/pdf/assessment_report.html', context)
    safe_name = assessment.name.replace(' ', '_')
    return render_pdf_response(html, f'{safe_name}_assessment_report.pdf', school=school)


@login_required
def class_term_reports_pdf_typed(request, class_name, report_type, term=None, academic_year=None):
    profile = get_profile(request.user)
    require_role(profile, ACADEMIC_PDF_ROLES)
    school = get_user_school(profile)

    term = term or school.active_term
    academic_year = academic_year or school.active_academic_year
    normalized = normalize_report_type(report_type)

    students = Student.objects.filter(
        school=school, current_class=class_name, is_active=True
    ).order_by('last_name', 'first_name')
    student_reports = [
        enrich_report_for_pdf(
            build_student_report_data(student, term, academic_year, normalized)
        )
        for student in students
    ]

    context = {
        'school': school,
        'school_logo_uri': image_file_uri(school.logo),
        'class_name': class_name,
        'term': term,
        'academic_year': academic_year,
        'report_title': report_type_label(normalized),
        'student_reports': student_reports,
    }
    html = render_to_string('core/pdf/class_all_report_cards.html', context)
    return render_pdf_response(html, f'{class_name}_{normalized}_reports.pdf', school=school)


@login_required
def student_report_pdf_typed(request, student_id, report_type):
    return student_report_pdf(request, student_id, report_type=report_type)


@login_required
def class_broadsheet_pdf(request, class_name, term=None, academic_year=None):
    profile = get_profile(request.user)
    require_role(profile, ACADEMIC_PDF_ROLES)
    school = get_user_school(profile)

    term = term or school.active_term
    academic_year = academic_year or school.active_academic_year

    students = Student.objects.filter(school=school, current_class=class_name).order_by('student_id')
    subjects = Subject.objects.filter(school=school, class_level=class_name)

    broadsheet = []
    for s in students:
        row = {'student': s, 'marks': []}
        for sub in subjects:
            entries = MarkEntry.objects.filter(student=s, subject=sub, grading_term=term, academic_year=academic_year)
            total_weighted = sum([e.weighted_score() for e in entries]) if entries else Decimal('0.00')
            grade = grade_from_score(float(total_weighted)) if total_weighted is not None else ''
            row['marks'].append({'subject': sub, 'total': total_weighted, 'grade': grade})
        broadsheet.append(row)

    ranked = []
    for row in broadsheet:
        total = sum((m['total'] for m in row['marks']), Decimal('0.00'))
        ranked.append({**row, 'grand_total': total})
    ranked.sort(key=lambda r: r['grand_total'], reverse=True)
    for i, row in enumerate(ranked, start=1):
        row['rank'] = i

    context = {
        **pdf_base_context(school),
        'class_name': class_name, 'term': term,
        'academic_year': academic_year, 'broadsheet': ranked, 'subjects': subjects,
    }
    html = render_to_string('core/pdf/class_broadsheet.html', context)
    return render_pdf_response(html, f'{class_name}_broadsheet_{academic_year}_{term}.pdf', school=school)


@login_required
def subject_performance_pdf(request, subject_id, term=None, academic_year=None):
    profile = get_profile(request.user)
    require_role(profile, SUBJECT_PDF_ROLES)
    school = get_user_school(profile)
    subject = get_object_or_404(Subject, pk=subject_id, school=school)
    term = term or school.active_term
    academic_year = academic_year or school.active_academic_year

    entries = MarkEntry.objects.filter(subject=subject, grading_term=term, academic_year=academic_year)
    counts = {'D1': 0, 'D2': 0, 'C3': 0, 'C4': 0, 'C5': 0, 'C6': 0, 'P7': 0, 'P8': 0, 'F9': 0}
    for e in entries:
        counts[e.grade()] = counts.get(e.grade(), 0) + 1

    student_rows = []
    by_student = {}
    for e in entries.select_related('student'):
        by_student.setdefault(e.student_id, {'student': e.student, 'scores': [], 'total': Decimal('0.00')})
        by_student[e.student_id]['scores'].append(e)
        by_student[e.student_id]['total'] += e.weighted_score()
    for data in by_student.values():
        avg = data['total']
        student_rows.append({
            'student': data['student'],
            'average': avg.quantize(Decimal('0.01')),
            'grade': grade_from_score(float(avg)),
        })
    student_rows.sort(key=lambda r: r['average'], reverse=True)

    context = {
        **pdf_base_context(school),
        'subject': subject, 'term': term,
        'academic_year': academic_year, 'counts': counts,
        'total': entries.count(), 'student_rows': student_rows,
    }
    html = render_to_string('core/pdf/subject_performance.html', context)
    return render_pdf_response(html, f'{subject.name}_performance_{academic_year}_{term}.pdf', school=school)


# ============================================================================
# NEW VIEWS FOR REDESIGNED DASHBOARD LAYOUT
# ============================================================================

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'core/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        user = self.request.user
        ctx['user_role'] = profile.role if profile else 'Unknown'
        ctx['school'] = get_user_school(profile)
        ctx['profile'] = profile
        ctx['form'] = UserProfileEditForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        form = UserProfileEditForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            if profile and form.cleaned_data.get('profile_picture'):
                profile.profile_picture = form.cleaned_data['profile_picture']
                profile.save()
            return redirect('core:profile')
        ctx = self.get_context_data(**kwargs)
        ctx['form'] = form
        return render(request, self.template_name, ctx)


class StudentProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'core/student_profile.html'

    def get_student(self):
        return get_object_or_404(Student, student_id=self.kwargs.get('student_id'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)

        student = self.get_student()
        if not can_view_student(profile, student):
            raise Http404()

        ctx['student'] = student
        ctx['fee_structure'] = student.get_fee_structure()
        ctx['total_paid'] = student.total_paid()
        ctx['balance'] = student.balance()
        ctx['payments'] = FeePaymentLedger.objects.filter(student=student).order_by('-date_of_payment')[:10]
        ctx['recent_marks'] = MarkEntry.objects.filter(
            student=student,
            academic_year=student.school.active_academic_year,
            grading_term=student.school.active_term
        ).select_related('subject', 'assessment_type').order_by('-recorded_at')[:20]
        ctx['can_edit'] = profile and profile.role in [
            'SUPER_ADMIN', 'SCHOOL_ADMIN', 'SECRETARY', 'HEAD_TEACHER', 'DOS'
        ]
        ctx['can_download_reports'] = True
        ctx['active_term'] = student.school.active_term
        ctx['active_year'] = student.school.active_academic_year
        ctx['edit_form'] = StudentEditForm(instance=student)
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        student = self.get_student()
        if not can_view_student(profile, student):
            raise Http404()

        action = request.POST.get('action')
        if action == 'upload_photo':
            photo = request.FILES.get('passport_photo')
            if photo:
                student.passport_photo = photo
                student.save(update_fields=['passport_photo'])
            return redirect('core:student_profile', student_id=student.student_id)

        if action == 'edit_profile' and profile.role in [
            'SUPER_ADMIN', 'SCHOOL_ADMIN', 'SECRETARY', 'HEAD_TEACHER', 'DOS'
        ]:
            form = StudentEditForm(request.POST, instance=student)
            if form.is_valid():
                form.save()
                return redirect('core:student_profile', student_id=student.student_id)
            ctx = self.get_context_data(**kwargs)
            ctx['edit_form'] = form
            return render(request, self.template_name, ctx)

        return redirect('core:student_profile', student_id=student.student_id)


class SearchStudentsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/search_students.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school

        q = self.request.GET.get('q', '').strip()
        selected_class = self.request.GET.get('class', '')
        selected_status = self.request.GET.get('status', '')

        ctx['search_query'] = q
        ctx['selected_class'] = selected_class
        ctx['selected_status'] = selected_status
        ctx['classes'] = SchoolClass.objects.filter(school=school) if school else []

        if school:
            students = Student.objects.filter(school=school)
            if q:
                students = students.filter(
                    Q(student_id__icontains=q)
                    | Q(first_name__icontains=q)
                    | Q(last_name__icontains=q)
                )
            if selected_class:
                students = students.filter(current_class=selected_class)
            if selected_status == 'active':
                students = students.filter(is_active=True)
            elif selected_status == 'inactive':
                students = students.filter(is_active=False)
            ctx['students'] = students.order_by('last_name', 'first_name')[:50]
        return ctx


# ADMIN VIEWS
class AdminSchoolsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/schools.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['school_form'] = SchoolSettingsForm(instance=school) if school else SchoolSettingsForm()
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        form = SchoolSettingsForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            from django.contrib import messages
            messages.success(request, f'School settings for "{school.school_name}" saved.')
            return redirect('core:admin_schools')
        from django.contrib import messages
        messages.error(request, 'Please correct the errors below.')
        ctx = self.get_context_data(**kwargs)
        ctx['school_form'] = form
        return render(request, self.template_name, ctx)


class AdminStaffView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/staff.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['staff_users'] = UserProfile.objects.filter(school=school).select_related('user') if school else []
        ctx['staff_form'] = StaffUserCreationForm(school=school)
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        action = request.POST.get('action')
        if action == 'delete_staff':
            staff = UserProfile.objects.filter(pk=request.POST.get('staff_id'), school=school).select_related('user').first()
            if staff:
                if profile.role == 'SUPER_ADMIN' or staff.role != 'SUPER_ADMIN':
                    if staff.user_id != request.user.id:
                        staff.user.delete()
            return redirect('core:admin_staff')

        staff_form = StaffUserCreationForm(request.POST, school=school)
        if staff_form.is_valid():
            user = get_user_model().objects.create_user(
                username=staff_form.cleaned_data['username'],
                email=staff_form.cleaned_data['email'],
                password=staff_form.cleaned_data['password'],
                first_name=staff_form.cleaned_data['first_name'],
                last_name=staff_form.cleaned_data['last_name'],
            )
            user_profile = UserProfile.objects.create(
                user=user,
                role=staff_form.cleaned_data['role'],
                school=school,
            )
            assigned_class = staff_form.cleaned_data.get('assigned_class')
            if assigned_class and staff_form.cleaned_data['role'] in ['CLASS_TEACHER', 'DOS', 'HEAD_TEACHER']:
                ClassTeacherAssignment.objects.get_or_create(
                    teacher=user_profile, school_class=assigned_class
                )
            teach_roles = ['CLASS_TEACHER', 'SUBJECT_TEACHER', 'DOS', 'HEAD_TEACHER']
            if staff_form.cleaned_data['role'] in teach_roles:
                for subject in staff_form.cleaned_data.get('assigned_subjects', []):
                    TeacherSubjectAssignment.objects.get_or_create(
                        teacher=user_profile,
                        subject=subject,
                        assigned_class=subject.class_level,
                    )
            return redirect('core:admin_staff')

        ctx = self.get_context_data(**kwargs)
        ctx['staff_form'] = staff_form
        return render(request, self.template_name, ctx)


class AdminClassesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/classes.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['class_form'] = SchoolClassForm()
        class_rows = []
        if school:
            for school_class in SchoolClass.objects.filter(school=school):
                assignment = ClassTeacherAssignment.objects.filter(
                    school_class=school_class
                ).select_related('teacher__user').first()
                class_rows.append({
                    'school_class': school_class,
                    'class_teacher': assignment.teacher if assignment else None,
                    'students_count': Student.objects.filter(
                        school=school, current_class=school_class.name, is_active=True
                    ).count(),
                })
        ctx['class_rows'] = class_rows
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        class_form = SchoolClassForm(request.POST)
        if class_form.is_valid():
            school_class = class_form.save(commit=False)
            school_class.school = school
            school_class.save()
            return redirect('core:admin_classes')
        ctx = self.get_context_data(**kwargs)
        ctx['class_form'] = class_form
        return render(request, self.template_name, ctx)


class AdminSubjectsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/subjects.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['subjects'] = Subject.objects.filter(school=school) if school else []
        ctx['subject_form'] = SubjectForm()
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        if request.POST.get('action') == 'delete_subject':
            Subject.objects.filter(pk=request.POST.get('subject_id'), school=school).delete()
            return redirect('core:admin_subjects')

        subject_form = SubjectForm(request.POST)
        if subject_form.is_valid():
            subject = subject_form.save(commit=False)
            subject.school = school
            subject.save()
            return redirect('core:admin_subjects')

        ctx = self.get_context_data(**kwargs)
        ctx['subject_form'] = subject_form
        return render(request, self.template_name, ctx)


class AdminAssessmentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/assessments.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['assessments'] = AssessmentType.objects.filter(school=school) if school else []
        ctx['assessment_form'] = AssessmentTypeForm()
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        if request.POST.get('action') == 'delete_assessment':
            AssessmentType.objects.filter(pk=request.POST.get('assessment_id'), school=school).delete()
            return redirect('core:admin_assessments')

        assessment_form = AssessmentTypeForm(request.POST)
        if assessment_form.is_valid():
            assessment = assessment_form.save(commit=False)
            assessment.school = school
            assessment.save()
            return redirect('core:admin_assessments')

        ctx = self.get_context_data(**kwargs)
        ctx['assessment_form'] = assessment_form
        return render(request, self.template_name, ctx)


class AdminAssignmentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/assignments.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        if school:
            ctx['teachers'] = UserProfile.objects.filter(school=school).select_related('user')
            ctx['classes'] = SchoolClass.objects.filter(school=school)
            ctx['subjects'] = Subject.objects.filter(school=school)
            ctx['class_assignments'] = ClassTeacherAssignment.objects.filter(
                school_class__school=school
            ).select_related('teacher__user', 'school_class')
            ctx['subject_assignments'] = TeacherSubjectAssignment.objects.filter(
                subject__school=school
            ).select_related('teacher__user', 'subject')
        else:
            ctx['teachers'] = []
            ctx['classes'] = []
            ctx['subjects'] = []
            ctx['class_assignments'] = []
            ctx['subject_assignments'] = []
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        action = request.POST.get('action')

        if action == 'assign_class_teacher':
            teacher = UserProfile.objects.filter(
                pk=request.POST.get('teacher_id'), school=school, role='CLASS_TEACHER'
            ).first()
            school_class = SchoolClass.objects.filter(
                pk=request.POST.get('class_id'), school=school
            ).first()
            if teacher and school_class:
                ClassTeacherAssignment.objects.get_or_create(
                    teacher=teacher, school_class=school_class
                )
        elif action == 'delete_class_assignment':
            ClassTeacherAssignment.objects.filter(
                pk=request.POST.get('assignment_id'), school_class__school=school
            ).delete()
        elif action == 'assign_subject_teacher':
            teacher = UserProfile.objects.filter(
                pk=request.POST.get('teacher_id'), school=school
            ).filter(role__in=['CLASS_TEACHER', 'SUBJECT_TEACHER']).first()
            subject = Subject.objects.filter(pk=request.POST.get('subject_id'), school=school).first()
            assigned_class = request.POST.get('assigned_class')
            if teacher and subject and assigned_class:
                TeacherSubjectAssignment.objects.get_or_create(
                    teacher=teacher,
                    subject=subject,
                    assigned_class=assigned_class,
                )
        elif action == 'delete_subject_assignment':
            TeacherSubjectAssignment.objects.filter(
                pk=request.POST.get('assignment_id'), subject__school=school
            ).delete()

        return redirect('core:admin_assignments')


class AdminFeesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/admin/fees.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['fee_structures'] = FeeStructure.objects.filter(school=school) if school else []
        ctx['fee_form'] = FeeStructureForm(school=school)
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        if not school:
            raise Http404()
        if request.POST.get('action') == 'delete_fee':
            FeeStructure.objects.filter(pk=request.POST.get('fee_id'), school=school).delete()
            return redirect('core:admin_fees')

        fee_form = FeeStructureForm(request.POST, school=school)
        if fee_form.is_valid():
            fee_struct = fee_form.save(commit=False)
            fee_struct.school = school
            if fee_struct.school_class and not fee_struct.target_class:
                fee_struct.target_class = fee_struct.school_class.name
            fee_struct.save()
            from django.contrib import messages
            messages.success(request, f'Fee "{fee_struct.fee_type}" added for {fee_struct.target_class}.')
            return redirect('core:admin_fees')

        from django.contrib import messages
        messages.error(request, 'Could not save fee structure. Check the form for errors.')
        ctx = self.get_context_data(**kwargs)
        ctx['fee_form'] = fee_form
        return render(request, self.template_name, ctx)


# BURSAR VIEWS
class BursarTermWorkflowView(RoleRequiredMixin, TemplateView):
    template_name = 'core/bursar/term_workflow.html'
    allowed_roles = ['BURSAR']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        school = get_user_school(profile)
        action = request.POST.get('action')
        if action == 'issue_demands':
            school.fees_demanded = True
            school.fees_demanded_at = timezone.now()
            school.save(update_fields=['fees_demanded', 'fees_demanded_at'])
        elif action == 'open_term':
            school.term_open_for_academics = True
            school.term_opened_at = timezone.now()
            school.save(update_fields=['term_open_for_academics', 'term_opened_at'])
        elif action == 'close_term':
            school.term_open_for_academics = False
            school.save(update_fields=['term_open_for_academics'])
        return redirect('core:bursar_term_workflow')


# HEAD TEACHER VIEWS
class HeadTeacherStudentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/head_teacher/students.html'
    allowed_roles = ['HEAD_TEACHER']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['students'] = Student.objects.filter(school=get_user_school(profile)).order_by('current_class', 'last_name')
        return ctx


class HeadTeacherClassesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/head_teacher/classes.html'
    allowed_roles = ['HEAD_TEACHER']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['classes'] = SchoolClass.objects.filter(school=get_user_school(profile))
        return ctx


class HeadTeacherReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/head_teacher/reports.html'
    allowed_roles = ['HEAD_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        school = get_user_school(profile)
        ctx['school'] = school
        ctx['top_students_by_class'] = []
        ctx['best_students_by_subject'] = []
        ctx['best_students_by_subject_in_class'] = []
        ctx['top_students_overall'] = []

        if school:
            ctx.update(build_academic_reports_context(school))

        return ctx


# CLASS TEACHER VIEWS
class ClassTeacherStudentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/class_teacher/students.html'
    allowed_roles = ['CLASS_TEACHER']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        
        # Get assigned class
        assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
        if assignment:
            ctx['assigned_class'] = assignment.school_class
            ctx['students'] = Student.objects.filter(
                school=get_user_school(profile),
                current_class=assignment.school_class.name
            ).order_by('last_name')
        return ctx


class ClassTeacherMarksView(RoleRequiredMixin, TemplateView):
    template_name = 'core/class_teacher/marks.html'
    allowed_roles = ['CLASS_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)

        assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
        if assignment:
            ctx['assigned_class'] = assignment.school_class
            ctx['subject_assignments'] = TeacherSubjectAssignment.objects.filter(teacher=profile)
            ctx.update(marks_page_context(profile, restrict_class=assignment.school_class.name))
        return ctx


class ClassTeacherPerformanceView(RoleRequiredMixin, TemplateView):
    template_name = 'core/class_teacher/performance.html'
    allowed_roles = ['CLASS_TEACHER', 'DOS', 'HEAD_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)

        assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
        class_name = self.request.GET.get('class')
        if assignment:
            ctx['assigned_class'] = assignment.school_class
            class_name = assignment.school_class.name
        elif class_name and get_user_school(profile):
            ctx['assigned_class'] = SchoolClass.objects.filter(
                school=get_user_school(profile), name=class_name
            ).first()

        if class_name and get_user_school(profile):
            school = get_user_school(profile)
            term = school.active_term
            year = school.active_academic_year
            students = Student.objects.filter(
                school=school, current_class=class_name, is_active=True,
            )
            ctx['students'] = students
            marks_qs = MarkEntry.objects.filter(
                student__in=students, grading_term=term, academic_year=year,
            )
            scores = [float(m.score_achieved) for m in marks_qs]
            ctx['marks_count'] = len(scores)
            ctx['students_with_marks'] = marks_qs.values('student_id').distinct().count()
            ctx['average_performance'] = round(sum(scores) / len(scores), 1) if scores else None
            ctx['chart_data'] = analytics_chart_data(marks_qs)
        return ctx


class ClassTeacherReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/class_teacher/reports.html'
    allowed_roles = ['CLASS_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)

        assignment = ClassTeacherAssignment.objects.filter(teacher=profile).first()
        if assignment:
            ctx['assigned_class'] = assignment.school_class
            ctx['students'] = Student.objects.filter(
                school=get_user_school(profile),
                current_class=assignment.school_class.name,
                is_active=True,
            ).order_by('last_name', 'first_name')
        return ctx


# SUBJECT TEACHER VIEWS
class SubjectTeacherMarksView(RoleRequiredMixin, TemplateView):
    template_name = 'core/subject_teacher/marks.html'
    allowed_roles = ['SUBJECT_TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        assignments = TeacherSubjectAssignment.objects.filter(teacher=profile)
        ctx['assignments'] = assignments
        subject_ids = list(assignments.values_list('subject_id', flat=True))
        if subject_ids:
            ctx.update(marks_page_context(profile, restrict_subject_ids=subject_ids))
            ctx['subjects'] = Subject.objects.filter(pk__in=subject_ids)
        return ctx


class SubjectTeacherReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/subject_teacher/reports.html'
    allowed_roles = ['SUBJECT_TEACHER']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['assignments'] = TeacherSubjectAssignment.objects.filter(teacher=profile)
        return ctx


# BURSAR VIEWS
class BursarFeesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/bursar/fees.html'
    allowed_roles = ['BURSAR']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['fee_structures'] = FeeStructure.objects.filter(school=get_user_school(profile))
        return ctx


class BursarPaymentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/bursar/payments.html'
    allowed_roles = ['BURSAR']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['form'] = FeePaymentForm(school=get_user_school(profile))
        ctx['payments'] = FeePaymentLedger.objects.filter(
            student__school=get_user_school(profile)
        ).select_related('student').order_by('-date_of_payment')[:100]
        return ctx

    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        form = FeePaymentForm(request.POST, school=get_user_school(profile))
        payment, form = record_payment_from_form(request, form, profile)
        if payment:
            return redirect(reverse('core:receipt_view', args=[payment.unique_receipt_id]))
        ctx = self.get_context_data(**kwargs)
        ctx['form'] = form
        return render(request, self.template_name, ctx)


class BursarReceiptsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/bursar/receipts.html'
    allowed_roles = ['BURSAR']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['receipts'] = FeePaymentLedger.objects.filter(student__school=get_user_school(profile)).order_by('-date_of_payment')[:100]
        return ctx


class BursarBalancesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/bursar/balances.html'
    allowed_roles = ['BURSAR']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)

        balances, total_outstanding = build_student_balances(get_user_school(profile))
        sort = self.request.GET.get('sort', 'name')
        if sort == 'balance':
            balances.sort(key=lambda item: item['balance'], reverse=True)
        else:
            balances.sort(key=lambda item: (item['student'].last_name, item['student'].first_name))

        ctx['student_balances'] = balances
        ctx['total_outstanding'] = total_outstanding
        ctx['total_students'] = len(balances)
        return ctx


class BursarReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/bursar/reports.html'
    allowed_roles = ['BURSAR']

    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        return ctx


# SECRETARY VIEWS
class SecretaryStudentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/secretary/students.html'
    allowed_roles = ['SECRETARY']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['students'] = Student.objects.filter(school=get_user_school(profile)).order_by('-enrollment_date')
        return ctx


class SecretaryEnrollView(RoleRequiredMixin, TemplateView):
    template_name = 'core/secretary/enroll.html'
    allowed_roles = ['SECRETARY']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        ctx['form'] = StudentRegistrationForm(school=get_user_school(profile))
        return ctx
    
    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        form = StudentRegistrationForm(request.POST, request.FILES, school=get_user_school(profile))
        if form.is_valid():
            persist_student_from_form(form, get_user_school(profile))
            return redirect('core:secretary_students')
        ctx = self.get_context_data(**kwargs)
        ctx['form'] = form
        return render(request, self.template_name, ctx)


class SecretaryMarksView(RoleRequiredMixin, TemplateView):
    template_name = 'core/secretary/marks.html'
    allowed_roles = ['SECRETARY']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        school = get_user_school(profile)
        ctx['school'] = school
        if school:
            ctx.update(marks_page_context(profile))
        return ctx


class SecretaryPaymentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/secretary/payments.html'
    allowed_roles = ['SECRETARY']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['form'] = FeePaymentForm(school=school)
        ctx['show_balances_link'] = False
        if school:
            ctx['payments'] = FeePaymentLedger.objects.filter(
                student__school=school
            ).select_related('student').order_by('-date_of_payment')[:100]
        else:
            ctx['payments'] = []
        return ctx
    
    def post(self, request, *args, **kwargs):
        profile = get_profile(request.user)
        form = FeePaymentForm(request.POST, school=get_user_school(profile))
        payment, form = record_payment_from_form(request, form, profile)
        if payment:
            return redirect(reverse('core:receipt_view', args=[payment.unique_receipt_id]))
        ctx = self.get_context_data(**kwargs)
        ctx['form'] = form
        return render(request, self.template_name, ctx)


# DOS VIEWS
class DOSStudentsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dos/students.html'
    allowed_roles = ['DOS']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = get_user_school(profile)
        students = Student.objects.filter(school=get_user_school(profile), is_active=True)
        class_filter = self.request.GET.get('class')
        if class_filter:
            students = students.filter(current_class=class_filter)
            ctx['selected_class'] = class_filter
        ctx['students'] = students.order_by('current_class', 'last_name')
        ctx['classes'] = SchoolClass.objects.filter(school=get_user_school(profile))
        return ctx


class DOSClassesView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dos/classes.html'
    allowed_roles = ['DOS']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        ctx['user_role'] = profile.role if profile else ''
        school = get_user_school(profile)
        ctx['school'] = school
        if school:
            ctx['class_summary'] = build_dos_class_summary(school)
        else:
            ctx['class_summary'] = []
        return ctx


class DOSReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'core/dos/reports.html'
    allowed_roles = ['DOS']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['user_role'] = profile.role if profile else ''
        ctx['school'] = school
        ctx['top_students_by_class'] = []
        ctx['best_students_by_subject'] = []
        ctx['class_summary'] = []

        if school:
            academic_ctx = build_academic_reports_context(school)
            ctx['classes'] = academic_ctx['classes']
            ctx['chart_data'] = academic_ctx['chart_data']
            ctx['best_students_by_subject'] = academic_ctx['best_students_by_subject']
            ctx['top_students_by_class'] = academic_ctx['top_students_by_class']

            term = school.active_term
            academic_year = school.active_academic_year
            students = Student.objects.filter(school=school, is_active=True)
            marks = MarkEntry.objects.filter(
                student__in=students,
                grading_term=term,
                academic_year=academic_year,
            ).select_related('student', 'subject')

            class_totals = {}
            class_counts = {}
            for mark in marks:
                class_name = mark.student.current_class
                class_totals.setdefault(class_name, Decimal('0.00'))
                class_totals[class_name] += mark.weighted_score()
                class_counts.setdefault(class_name, set()).add(mark.student_id)

            for class_name, total_score in class_totals.items():
                count = len(class_counts.get(class_name, set()))
                ctx['class_summary'].append({
                    'class_name': class_name,
                    'student_count': count,
                    'average_score': (total_score / count).quantize(Decimal('0.01')) if count else Decimal('0.00'),
                })

        return ctx


# ============================================================================
# QR CODE FOR MOBILE/LAN ACCESS
# ============================================================================

import qrcode
from io import BytesIO
import uuid


def generate_qr_code_data_url(url, size=300):
    """Generate a QR code as a data URL for embedding in HTML."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    import base64
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def get_base_url(request):
    """Get the base URL for the application."""
    if request:
        return request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    return 'http://localhost:8000'


class QRCodeConnectView(TemplateView):
    """Display QR code for members to connect via phone LAN."""
    template_name = 'core/qr_connect.html'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN', 'SECRETARY', 'BURSAR', 'HEAD_TEACHER', 'DOS']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        school = get_user_school(profile)
        ctx['school'] = school
        ctx['user_role'] = profile.role if profile else ''
        
        # Generate base URL
        base_url = get_base_url(self.request)
        login_url = f"{base_url}/accounts/login/"
        
        # Generate QR code
        ctx['qr_code_url'] = generate_qr_code_data_url(login_url)
        ctx['login_url'] = login_url
        ctx['school_name'] = school.school_name if school else 'School Management System'
        
        return ctx


def qr_code_image(request):
    """Return QR code image directly for downloading."""
    profile = get_profile(request.user)
    school = get_user_school(profile)
    
    base_url = get_base_url(request)
    login_url = f"{base_url}/accounts/login/"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(login_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    from django.http import HttpResponse
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="school_connect_qr.png"'
    return response
