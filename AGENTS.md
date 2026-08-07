# School Management System - Agent Knowledge Base

## Project Overview
A comprehensive Django-based school management system with support for multiple schools, user roles, fee management, marks/grades, and academic reporting. Commercial-grade with HWID licensing, RBAC, and offline-first desktop support.

## Key Technologies
- Django 6.1 with SQLite
- Bootstrap 5 for frontend
- QR Code generation (qrcode library)
- PDF generation (reportlab)
- Licensing system with feature flags
- Hardware-bound licensing (HWID)
- RBAC with 8 distinct roles

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

## Important URLs
### Authentication
- Login: /accounts/login/
- Dashboard: / (auto-redirects based on role)

### Master Vendor (Software Owner)
- /master-vendor/ - Vendor Dashboard
- /system/license-status/ - License Status & Upgrade
- /master-vendor/schools/ - School Management
- /master-vendor/users/ - User Management
- /master-vendor/feature-matrix/ - Feature Matrix
- /master-vendor/backups/ - Backup Management
- /master-vendor/audit/ - Audit Log
- /master-vendor/branding/ - Branding Control

### Academic
- /head-teacher/ - Executive Dashboard
- /dos/ - Academic Management
- /class-teacher/ - Class Management
- /subject-teacher/ - Subject Marks

### Finance
- /bursar/ - Bursar Dashboard

### Communication
- /notifications/whatsapp-queue/ - WhatsApp Message Queue
- /notifications/email-queue/ - Email Queue
- /notifications/templates/ - Message Templates

### Other
- /qr-connect/ - QR Code for Mobile/LAN
- /parent-kiosk/ - Parent Portal
- /licensing/manage/ - License Management
- /licensing/emergency-recovery/ - Password Recovery
- /dos/termly-return/ - Termly Return Checker
- /dos/batch-id-cards/ - A4 Batch ID Cards

## Feature Flags (Licensing)
- PHOTO_UPLOAD
- ID_GENERATOR
- PARENT_KIOSK
- PDF_PREVIEW
- BATCH_PROMOTION
- FINANCE_REPORTS
- SMS_REPORTS
- ATTENDANCE
- CLOUD_SYNC
- ADVANCED_ANALYTICS

## Hardware-Bound Licensing
- HWID calculated from CPU, disk serial, MAC address
- EncryptedFeatureMatrix model for matrix key validation
- check_hwid_match() validates machine binding
- EmergencyRecoveryToken for password recovery
- License Status & Upgrade view at /system/license-status/

## Messaging System
- WhatsApp Web Queue (/notifications/whatsapp-queue/)
- Email SMTP Dispatcher (utils/email_dispatcher.py)
- Pre-formatted wa.me links
- BCC mode for privacy

## Backup System
- Location: /backups/
- CLI: python -m backups.backup_service [backup|auto|sync-usb|sync-cloud|list]

## Database Migrations
```bash
python manage.py makemigrations --settings=django_sms.settings
python manage.py migrate --settings=django_sms.settings
```

## Running the Server
```bash
python manage.py runserver 0.0.0.0:8000 --settings=django_sms.settings
```
