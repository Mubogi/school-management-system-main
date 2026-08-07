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
