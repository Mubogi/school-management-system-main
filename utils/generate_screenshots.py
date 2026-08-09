#!/usr/bin/env python3
"""
Automated Screenshot Generation Script
Generates real PNG screenshots for all major pages using Playwright.
Run with the Django server on port 12000:
    python manage.py runserver 0.0.0.0:12000 --settings=django_sms.settings
    python utils/generate_screenshots.py
"""
import os
import sys
import time
from pathlib import Path

BASE_URL = "http://localhost:12000"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
USERNAME = "jordan"
PASSWORD = "20020120"


def setup_playwright():
    """Setup Playwright for screenshots."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    return playwright, browser, context, page


def login(page):
    """Login to the system as the Jordan admin."""
    page.goto(f"{BASE_URL}/accounts/login/")
    time.sleep(2)
    page.fill("input[name='username']", USERNAME)
    page.fill("input[name='password']", PASSWORD)
    page.click("button[type='submit']")
    time.sleep(3)


def shot(page, label, filename, section=None):
    """Take a single screenshot with label tracking."""
    tag = f"[{section}] {label}" if section else label
    print(f"  {tag}")
    time.sleep(1)
    filepath = SCREENSHOTS_DIR / filename
    page.screenshot(path=str(filepath), full_page=False)
    size_kb = filepath.stat().st_size / 1024
    print(f"    ✓ {filename} ({size_kb:.0f} KB)")


def goto(page, path, wait=2):
    """Navigate and wait."""
    page.goto(f"{BASE_URL}{path}")
    time.sleep(wait)


def generate_screenshots():
    """Generate all required screenshots."""
    print("\n🖼️  JD Hub School Management System - Screenshot Generator")
    print("=" * 60)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    playwright = None
    try:
        print("\n📸 Starting screenshot generation...")
        playwright, browser, context, page = setup_playwright()
        page.set_default_timeout(15000)

        # ---- PUBLIC PAGES ----
        print("\n=== PUBLIC PAGES ===")
        goto(page, "/")
        shot(page, "Landing Page", "01_landing_page.png", "PUBLIC")
        goto(page, "/setup/")
        shot(page, "First Run Setup", "02_first_run_setup.png", "PUBLIC")
        goto(page, "/accounts/login/")
        shot(page, "Login Page", "03_login.png", "PUBLIC")
        goto(page, "/parent-kiosk/")
        shot(page, "Parent Kiosk", "04_parent_kiosk.png", "PUBLIC")
        goto(page, "/qr-connect/")
        shot(page, "QR Connect", "05_qr_connect.png", "PUBLIC")

        # ---- MASTER VENDOR ----
        print("\n=== MASTER VENDOR PANEL ===")
        login(page)
        goto(page, "/master-vendor/", wait=3)
        shot(page, "Master Vendor Dashboard", "06_master_vendor_dashboard.png", "VENDOR")
        goto(page, "/master-vendor/schools/")
        shot(page, "School Management", "07_vendor_schools.png", "VENDOR")
        goto(page, "/master-vendor/users/")
        shot(page, "User Management", "08_vendor_users.png", "VENDOR")
        goto(page, "/master-vendor/feature-matrix/")
        shot(page, "Feature Matrix", "09_feature_matrix.png", "VENDOR")
        goto(page, "/master-vendor/backups/")
        shot(page, "Backup Management", "10_vendor_backups.png", "VENDOR")
        goto(page, "/master-vendor/audit/")
        shot(page, "Audit Log", "11_audit_log.png", "VENDOR")
        goto(page, "/master-vendor/statistics/")
        shot(page, "Platform Statistics", "12_vendor_statistics.png", "VENDOR")

        # ---- LICENSING ----
        print("\n=== LICENSING ===")
        goto(page, "/system/license-status/")
        shot(page, "License Status", "13_license_status.png", "LICENSE")
        goto(page, "/licensing/manage/")
        shot(page, "License Management", "14_license_management.png", "LICENSE")

        # ---- ACADEMIC DASHBOARDS ----
        print("\n=== ACADEMIC ===")
        goto(page, "/super-admin/")
        shot(page, "School Admin Dashboard", "15_school_admin_dashboard.png", "ACADEMIC")
        goto(page, "/head-teacher/")
        shot(page, "Head Teacher Dashboard", "16_head_teacher_dashboard.png", "ACADEMIC")
        goto(page, "/dos/")
        shot(page, "DOS Academic Management", "17_dos_dashboard.png", "ACADEMIC")
        goto(page, "/dos/batch-id-cards/")
        shot(page, "Batch ID Cards", "18_batch_id_cards.png", "ACADEMIC")
        goto(page, "/dos/termly-return/")
        shot(page, "Termly Return Checker", "19_termly_return.png", "ACADEMIC")
        goto(page, "/marks/bulk/")
        shot(page, "Bulk Marks Entry", "20_marks_bulk_entry.png", "ACADEMIC")

        # ---- FINANCE ----
        print("\n=== FINANCE ===")
        goto(page, "/bursar/")
        shot(page, "Bursar Dashboard", "21_bursar_dashboard.png", "FINANCE")
        goto(page, "/bursar/fees/")
        shot(page, "Fee Structures", "22_fee_structures.png", "FINANCE")
        goto(page, "/bursar/payments/")
        shot(page, "Payment Recording", "23_payment_recording.png", "FINANCE")
        goto(page, "/bursar/receipts/")
        shot(page, "Receipts", "24_receipts.png", "FINANCE")

        # ---- STUDENT MANAGEMENT ----
        print("\n=== STUDENT MANAGEMENT ===")
        goto(page, "/secretary/students/")
        shot(page, "Student List", "25_student_list.png", "STUDENT")
        goto(page, "/secretary/enroll/")
        shot(page, "Student Enrollment", "26_student_enroll.png", "STUDENT")

        # ---- COMMUNICATION ----
        print("\n=== COMMUNICATION ===")
        goto(page, "/notifications/whatsapp-queue/")
        shot(page, "WhatsApp Queue", "27_whatsapp_queue.png", "COMM")
        goto(page, "/notifications/email-queue/")
        shot(page, "Email Queue", "28_email_queue.png", "COMM")
        goto(page, "/notifications/templates/")
        shot(page, "Message Templates", "29_message_templates.png", "COMM")

        print("\n" + "=" * 60)
        print("✅ All screenshots generated successfully!")
        print(f"📁 Location: {SCREENSHOTS_DIR}")
        files = sorted(SCREENSHOTS_DIR.glob("*.png"))
        print(f"📋 {len(files)} files generated:")
        for i, f in enumerate(files, 1):
            size = f.stat().st_size / 1024
            print(f"   {i:02d}. {f.name} ({size:.1f} KB)")

    except ImportError as e:
        print(f"\n⚠️  Playwright not installed: {e}")
        print("   pip install playwright && python -m playwright install chromium")

    except Exception as e:
        print(f"\n❌ Error generating screenshots: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if playwright:
            playwright.stop()

    return True


if __name__ == "__main__":
    print("\n🔧 Prerequisites:")
    print("  1. Start Django server: python manage.py runserver 0.0.0.0:12000")
    print("  2. Install Playwright: pip install playwright")
    print("  3. Install browsers: python -m playwright install chromium\n")
    generate_screenshots()
