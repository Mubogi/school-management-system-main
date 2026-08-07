#!/usr/bin/env python3
"""
Automated Screenshot Generation Script
Generates screenshots for all major features using Playwright
and saves to /screenshots folder.
"""
import os
import sys
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
USERNAME = "Jordan"
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
    """Login to the system."""
    page.goto(f"{BASE_URL}/accounts/login/")
    time.sleep(2)
    
    # Fill login form
    page.fill("input[name='username']", USERNAME)
    page.fill("input[name='password']", PASSWORD)
    
    # Submit
    page.click("button[type='submit']")
    time.sleep(3)


def take_screenshot(page, filename):
    """Take a screenshot and save to file."""
    time.sleep(1)  # Allow page to stabilize
    filepath = SCREENSHOTS_DIR / filename
    page.screenshot(path=str(filepath), full_page=False)
    print(f"  ✓ Saved: {filename}")


def generate_screenshots():
    """Generate all required screenshots."""
    print("\n🖼️  JD Hub School Management System - Screenshot Generator")
    print("=" * 60)
    
    # Ensure screenshots directory exists
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    
    playwright = None
    
    try:
        print("\n📸 Starting screenshot generation...")
        playwright, browser, context, page = setup_playwright()
        
        # 1. Landing Page
        print("\n  [1/10] Landing Page")
        page.goto(BASE_URL)
        time.sleep(2)
        take_screenshot(page, "01_landing_page.png")
        
        # 2. First Run Setup (if no admin)
        print("\n  [2/10] First Run Setup")
        page.goto(f"{BASE_URL}/setup/")
        time.sleep(2)
        take_screenshot(page, "02_first_run_setup.png")
        
        # 3. Login
        print("\n  [3/10] Login Page")
        page.goto(f"{BASE_URL}/accounts/login/")
        time.sleep(2)
        take_screenshot(page, "03_login.png")
        
        # 4. Login and access dashboard
        print("\n  [4/10] Master Vendor Dashboard")
        login(page)
        page.goto(f"{BASE_URL}/master-vendor/")
        time.sleep(3)
        take_screenshot(page, "04_master_vendor_dashboard.png")
        
        # 5. License Status
        print("\n  [5/10] License Status")
        page.goto(f"{BASE_URL}/system/license-status/")
        time.sleep(2)
        take_screenshot(page, "05_license_status.png")
        
        # 6. School Admin Dashboard
        print("\n  [6/10] School Admin Dashboard")
        page.goto(f"{BASE_URL}/super-admin/")
        time.sleep(2)
        take_screenshot(page, "06_school_admin_dashboard.png")
        
        # 7. WhatsApp Queue
        print("\n  [7/10] WhatsApp Queue")
        page.goto(f"{BASE_URL}/notifications/whatsapp-queue/")
        time.sleep(2)
        take_screenshot(page, "07_whatsapp_queue.png")
        
        # 8. Student Management
        print("\n  [8/10] Student Management")
        page.goto(f"{BASE_URL}/secretary/students/")
        time.sleep(2)
        take_screenshot(page, "08_student_management.png")
        
        # 9. QR Connect
        print("\n  [9/10] QR Connect")
        page.goto(f"{BASE_URL}/qr-connect/")
        time.sleep(2)
        take_screenshot(page, "09_qr_connect.png")
        
        # 10. Parent Kiosk
        print("\n  [10/10] Parent Kiosk")
        page.goto(f"{BASE_URL}/parent-kiosk/")
        time.sleep(2)
        take_screenshot(page, "10_parent_kiosk.png")
        
        print("\n" + "=" * 60)
        print("✅ All screenshots generated successfully!")
        print(f"📁 Location: {SCREENSHOTS_DIR}")
        
        # List all screenshots
        print("\n📋 Generated Files:")
        for i, f in enumerate(sorted(SCREENSHOTS_DIR.glob("*.png")), 1):
            size = f.stat().st_size / 1024
            print(f"   {i:02d}. {f.name} ({size:.1f} KB)")
        
    except ImportError as e:
        print(f"\n⚠️  Playwright not installed: {e}")
        print("\n🔧 Install with:")
        print("   pip install playwright")
        print("   playwright install chromium")
        print("\n📝 Alternative: Use Selenium")
        print("   pip install selenium webdriver-manager")
        
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
    print("  1. Start Django server: python manage.py runserver 0.0.0.0:8000")
    print("  2. Install Playwright: pip install playwright")
    print("  3. Install browsers: playwright install chromium\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        input("\nPress Enter when server is ready...")
    
    generate_screenshots()
