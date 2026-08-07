# School Management System - Agent Knowledge Base

## Project Overview
A comprehensive Django-based school management system with support for multiple schools, user roles, fee management, marks/grades, and academic reporting.

## Key Technologies
- Django 6.1 with SQLite
- Bootstrap 5 for frontend
- QR Code generation (qrcode library)
- PDF generation (reportlab)
- Licensing system with feature flags
- Hardware-bound licensing (HWID)

## User Roles
- SUPER_ADMIN: Full system access
- SCHOOL_ADMIN: School-level admin
- HEAD_TEACHER: Academic leadership
- CLASS_TEACHER: Class-level management
- SUBJECT_TEACHER: Subject-specific marks
- BURSAR: Fee management
- SECRETARY: Student enrollment
- DOS: Director of Studies

## Important URLs
- Login: /accounts/login/
- Dashboard: / (auto-redirects based on role)
- QR Connect: /qr-connect/
- License: /licensing/manage/
- Emergency Recovery: /licensing/emergency-recovery/
- Feature Matrix: /licensing/matrix/activate/
- Parent Kiosk: /parent-kiosk/
- Termly Return: /dos/termly-return/
- Batch ID Cards: /dos/batch-id-cards/

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

## Backup System
- Location: /backups/
- auto_backup() for scheduled backups
- sync_to_usb() for USB sync
- check_online_and_sync() for cloud backup
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
