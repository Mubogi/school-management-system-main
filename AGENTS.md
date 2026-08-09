# School Management System - Agent Knowledge Base

## Project Overview
**JD Hub School Management System** - A commercial, offline-first school management application developed by Jordan Design Hub (JD Hub).

- **Developer**: Jordan Design Hub (JD Hub)
- **Contact**: +256 754 687 597, jordandesignhub@gmail.com
- **License**: Proprietary, HWID-bound desktop application

## Key Technologies
- Django 6.1 with SQLite
- Bootstrap 5 for frontend
- QR Code generation (qrcode library)
- PDF generation (reportlab)
- Licensing system with feature flags
- Hardware-bound licensing (HWID)
- RBAC with 9 distinct roles
- PyWebView for desktop wrapper

## User Roles (RBAC)
- MASTER_VENDOR: Software owner - full system control
- SCHOOL_ADMIN: School-level admin - user management, settings
- HEAD_TEACHER: Principal/Executive - academic analytics, report approval
- DOS: Director of Studies - terms, timetable, grading, exams
- ACCOUNTANT: Bursar/Finance - fees, payments, receipts
- SECRETARY: Admissions - student registration, contact details
- CLASS_TEACHER: Form Master - class dashboard, termly returns
- SUBJECT_TEACHER: Educator - marks entry for assigned subjects
- PARENT: Kiosk/PWA - read-only report cards and fee summaries

## RBAC System
- Location: core/rbac.py
- Decorators: @role_required(), @permission_required()
- Mixins: RoleRequiredMixin, MasterVendorMixin, SchoolAdminMixin, etc.
- Hierarchy: MASTER_VENDOR > SCHOOL_ADMIN > HEAD_TEACHER > DOS > ACCOUNTANT > SECRETARY > CLASS_TEACHER > SUBJECT_TEACHER > PARENT

## First-Run Setup
- URL: /setup/
- Creates initial Jordan admin (password: 20020120)
- Configures school details
- Displays HWID for binding
- Creates demo license

## Important URLs
### Public Pages
- / - Landing page with JD Hub branding
- /setup/ - First-run setup wizard
- /parent-kiosk/ - Parent portal (QR kiosk)
- /qr-connect/ - Mobile QR code access

### Authentication
- /accounts/login/ - Staff login
- /accounts/logout/ - Logout

### Master Vendor (Software Owner)
- /master-vendor/ - Vendor Dashboard
- /system/license-status/ - License Status & Upgrade
- /master-vendor/schools/ - School Management
- /master-vendor/users/ - User Management
- /master-vendor/feature-matrix/ - Feature Matrix
- /master-vendor/backups/ - Backup Management
- /master-vendor/audit/ - Audit Log

### Academic
- /head-teacher/ - Executive Dashboard
- /dos/ - Academic Management
- /class-teacher/ - Class Management
- /subject-teacher/ - Subject Marks

### Finance
- /bursar/ - Bursar Dashboard
- /bursar/fees/ - Fee Structures
- /bursar/payments/ - Payment Recording
- /bursar/receipts/ - Receipts

### Communication
- /notifications/whatsapp-queue/ - WhatsApp Message Queue
- /notifications/email-queue/ - Email Queue
- /notifications/templates/ - Message Templates

### Student Management
- /secretary/students/ - Student List
- /secretary/enroll/ - New Enrollment
- /dos/batch-id-cards/ - A4 Batch ID Cards
- /dos/termly-return/ - Termly Return Checker

### Other
- /licensing/manage/ - License Management
- /licensing/emergency-recovery/ - Password Recovery
- /system/license-status/ - View & Upgrade License

## Feature Flags (Licensing)
- PHOTO_UPLOAD - Student photos
- ID_GENERATOR - ID card generation
- PARENT_KIOSK - Parent portal access
- PDF_PREVIEW - PDF viewers
- BATCH_PROMOTION - Bulk promotions
- FINANCE_REPORTS - Financial reports
- SMS_REPORTS - SMS features
- ATTENDANCE - Attendance tracking
- CLOUD_SYNC - Cloud backup
- ADVANCED_ANALYTICS - Analytics dashboard

## Hardware-Bound Licensing
- HWID calculated from CPU, disk serial, MAC address
- Location: licensing/hwid.py
- EncryptedFeatureMatrix model for matrix key validation
- EmergencyRecoveryToken for password recovery
- License Status view at /system/license-status/

## Messaging System
- WhatsApp Web Queue (/notifications/whatsapp-queue/)
- Email SMTP Dispatcher (utils/email_dispatcher.py)
- Pre-formatted wa.me links
- BCC mode for privacy

## Screenshots
- Location: /screenshots/
- Generator: utils/generate_screenshots.py (Selenium)
- 10 screenshots for feature documentation

## Backup System
- Location: /backups/
- CLI: python -m backups.backup_service [backup|auto|sync-usb|sync-cloud|list]

## Desktop App
- Entry point: main.py (PyWebView wrapper)
- Binds to: 0.0.0.0:8000 for LAN access
- PWA support: manifest.json, sw.js
- Auto-migrate: main.py runs `migrate` on startup (ensure_database) so first run works without manual setup
- Browser fallback: if pywebview cannot start a GUI window (headless/missing GTK/QT), the app falls back to opening the system browser while the Django server keeps running

## PyInstaller Build (onedir)
- Spec file: `school_system.spec`
- Runtime hook: `school_system_rt_hook.py` (sets DJANGO_SETTINGS_MODULE + sys.path for frozen Django)
- Build command: `python build.py` or `python -m PyInstaller --noconfirm school_system.spec`
- Output: `dist/JDHubSchoolSystem/` (onedir, ~310MB)
- Frozen data layout (see `DATA_DIR` in settings.py):
  - `sys._MEIPASS` / `_internal/` — read-only bundled code/templates/static (PyInstaller)
  - `DATA_DIR` = directory next to the executable — writable user data: `db.sqlite3`, `media/`, `backups/`
  - Non-frozen (dev): DATA_DIR == BASE_DIR (project root), behavior unchanged
- Hidden imports collected via `collect_submodules` for django, all project apps, whitenoise, reportlab, qrcode, PIL, pywebview
- User data (db.sqlite3, media, backups) is excluded from the bundle and created at runtime

## Database Migrations
```bash
python manage.py makemigrations --settings=django_sms.settings
python manage.py migrate --settings=django_sms.settings
```

## Running the Server
```bash
python manage.py runserver 0.0.0.0:8000 --settings=django_sms.settings
python main.py  # Desktop app with PyWebView
```

## Apex UI Theme (light/dark toggle)
- Shared assets: `core/static/core/css/apex-theme.css` + `core/static/core/js/apex-theme.js`
- Mechanism: `data-theme="light|dark"` attr on `<html>`, persisted in `localStorage('theme')`.
- No-flash: each base template has an inline `<script>` in `<head>` that sets `data-theme`
  before paint (default `dark` when no stored pref).
- Toggle button: `<button class="apex-theme-toggle" data-apex-toggle ...>`. Binding is done
  in `apex-theme.js` via `addEventListener` (NOT inline `onclick` — inline onclick caused a
  double-fire that canceled the toggle). `bindToggles()` guards with `__apexBound` and runs
  on `readyState` interactive/complete or `DOMContentLoaded`.
- Two base layouts carry the toggle + imports:
  - `core/layout/base_layout.html` (Tailwind) — dashboards, staff, bursar, etc.
  - `core/base.html` (Bootstrap) — master-vendor and older views.
  - `school/base.html` (Bootstrap variant).
- Standalone pages (own `<style>` blocks, hardcoded colors) carry inline dark OR light
  overrides via `[data-theme="dark"]` / `[data-theme="light"]` selectors:
  - `qr_connect.html`, `licensing/activate.html`, kiosk pages → dark overrides (light default)
  - `home.html`, `setup_wizard.html` → light overrides (dark default)
- `apex-theme.css` overrides Tailwind utility classes in dark mode (e.g. `bg-white` → dark).
- Verified: toggle works bidirectionally on Tailwind dashboards, Bootstrap master-vendor,
  qr-connect, licensing/activate, parent-kiosk; theme persists across navigation.

### Known issues (pre-existing, NOT from theme work)
- `licensing/management.html` and `licensing/sessions.html` `{% extends 'core/layout/sidebar_nav.html' %}`
  but `sidebar_nav.html` is only a `{% block sidebar %}` partial with no HTML shell — so those
  two pages render only the sidebar nav (no `<head>`, CSS, or toggle). They need to extend a
  full base (e.g. `core/layout/base_layout.html`) instead.
- `home.html` is never rendered: `HomeView` redirects authed users to their role dashboard and
  unauthed users to login. The landing template is effectively dead.

### Dev server template caching
`runserver --noreload` serves cached compiled templates. After editing a template, restart
the server (kill the PID, relaunch) for changes to take effect. Browser may also cache the
HTML; use `?v=N` query param to bust.

## Apex PDF Theme
All PDF outputs use the Apex design system. Renderer priority in `render_pdf_response()`
(core/views.py): Playwright/Chromium → **WeasyPrint** → xhtml2pdf → ReportLab text fallback.
In this environment only WeasyPrint is installed and working (supports gradients, CSS grid,
inline SVG, `@page` margin boxes, system fonts via fontconfig).

### Fonts
Plus Jakarta Sans + JetBrains Mono are installed at `/usr/share/fonts/truetype/apex/`
(system-wide, registered with fontconfig). WeasyPrint resolves them by family name. If
absent, templates fall back to DejaVu Sans / DejaVu Sans Mono.

### Shared PDF assets (core/templates/core/pdf/)
- `apex_pdf_base.html` — `{% include %}` once per template; provides CSS variables
  (`--apex-primary` #4f46e5, `--apex-violet` #7c3aed, `--apex-pink` #db2777, etc.), `@page`
  footer, and reusable classes: `.apex-table` (dark header + zebra rows), `.apex-grade-pill`
  (D1–F9 color-coded), `.apex-summary-box` (dashed 3-col grid), `.apex-id-tag`,
  `.apex-watermark` / `.apex-watermark-glyph`, `.apex-logo-badge`.
- `apex_svg.html` — inline Lucide-compatible SVG glyphs: `{% include 'core/pdf/apex_svg.html' with icon='shield' %}`.
  Supported: shield, user, file-text, download, printer, key, contact, building, phone, graduation, check.
- `letterhead.html` — Apex gradient crest bar (3-color), gradient badge fallback when no logo,
  uppercase motto, double-rule divider. Included by receipt + most financial PDFs.

### Report cards (report_card_fragment.html)
Apex paper-sheet: school header (logo badge + name + motto + contact + OFFICIAL REPORT tag),
student profile strip (photo + name + ID pill + class + rank pill), marks table (dark header,
per-assessment details, mono weighted score, grade pill), summary stats box (avg/grade/attendance),
remarks (class teacher / DOS / head teacher), footer (digital verification key + signature).
Watermark: shield glyph + rotated uppercase school name at 4% opacity behind content.

### Student ID cards (student_id_cards.html)
- CR80 landscape cards on A4 portrait, 2 columns × 4 rows = 8 cards per sheet.
- Front: gradient security pattern, school header, photo frame, student name + role,
  meta grid (ID / class / DOB / expiry), gradient footer strip.
- Back: magnetic stripe, property-of terms, emergency contact, signature, barcode (student ID).
- Cut guides: dashed borders between card slots; back rows are column-mirrored so duplex
  printing aligns front↔back after cutting. `?faces=front|back|both` controls which sides render.
- View: `student_id_cards_pdf` in `core/super_admin_views.py` (SUPER_ADMIN only) passes
  `image_file_uri()` for photos/logos so WeasyPrint can embed local files.

### Other PDFs (palette + font swap)
financial_statement, fee_clearance_certificate, bursar_demand_letter, bursar_fee_report,
fee_clearance_list, fee_outstanding_list, assessment_report, class_broadsheet, report_card,
student_report, subject_performance, class_all_report_cards — all swapped from Segoe UI →
Plus Jakarta Sans and old blue palette (#1e40af/#3b82f6/#8b5cf6/#6366f1/#ec4899) → Apex
(#4f46e5/#7c3aed/#db2777). They include `letterhead.html` which carries the full Apex branding.

### ReportLab native generators (fallback path)
`generate_reportcard_reportlab_bytes()` and `generate_reportcard_modern_bytes()` in core/views.py
build PDFs natively with ReportLab Platypus (not HTML). These are only used when the HTML→PDF
renderers all fail. They retain their own hardcoded colors (teal/coral) — acceptable as a
last-resort fallback since the primary path is WeasyPrint + Apex HTML templates.
