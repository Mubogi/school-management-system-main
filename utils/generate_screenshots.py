#!/usr/bin/env python3
"""
Automated Screenshot Generation Script
Generates screenshots for all major features and saves to /screenshots folder.
"""
import os
import sys
import django
import time
import base64
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_sms.settings')
django.setup()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


# Configuration
BASE_URL = "http://localhost:8000"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
USERNAME = "Jordan"
PASSWORD = "20020120"


def setup_driver():
    """Setup Chrome driver for screenshots."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception:
        # Fallback to chromium
        driver = webdriver.Chrome(options=chrome_options)
    
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(30)
    return driver


def login(driver):
    """Login to the system."""
    driver.get(f"{BASE_URL}/accounts/login/")
    time.sleep(2)
    
    # Fill login form
    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")
    
    username_input.clear()
    username_input.send_keys(USERNAME)
    
    password_input.clear()
    password_input.send_keys(PASSWORD)
    
    # Submit
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)


def take_screenshot(driver, filename, wait_for_url=None):
    """Take a screenshot and save to file."""
    if wait_for_url:
        WebDriverWait(driver, 10).until(EC.url_contains(wait_for_url))
    
    time.sleep(1)  # Allow page to stabilize
    
    filepath = SCREENSHOTS_DIR / filename
    driver.save_screenshot(str(filepath))
    print(f"  ✓ Saved: {filename}")


def generate_screenshots():
    """Generate all required screenshots."""
    print("\n🖼️  JD Hub School Management System - Screenshot Generator")
    print("=" * 60)
    
    # Ensure screenshots directory exists
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    
    driver = None
    
    try:
        print("\n📸 Starting screenshot generation...")
        driver = setup_driver()
        
        # 1. Landing Page
        print("\n  [1/10] Landing Page")
        driver.get(BASE_URL)
        time.sleep(2)
        take_screenshot(driver, "01_landing_page.png")
        
        # 2. First Run Setup (if no admin)
        print("\n  [2/10] First Run Setup")
        driver.get(f"{BASE_URL}/setup/")
        time.sleep(2)
        take_screenshot(driver, "02_first_run_setup.png")
        
        # 3. Login
        print("\n  [3/10] Login")
        driver.get(f"{BASE_URL}/accounts/login/")
        time.sleep(2)
        take_screenshot(driver, "03_login.png")
        
        # 4. Login and access dashboard
        print("\n  [4/10] Master Vendor Dashboard")
        login(driver)
        driver.get(f"{BASE_URL}/master-vendor/")
        time.sleep(3)
        take_screenshot(driver, "04_master_vendor_dashboard.png")
        
        # 5. License Status
        print("\n  [5/10] License Status")
        driver.get(f"{BASE_URL}/system/license-status/")
        time.sleep(2)
        take_screenshot(driver, "05_license_status.png")
        
        # 6. School Admin Dashboard
        print("\n  [6/10] School Admin Dashboard")
        driver.get(f"{BASE_URL}/super-admin/")
        time.sleep(2)
        take_screenshot(driver, "06_school_admin_dashboard.png")
        
        # 7. WhatsApp Queue
        print("\n  [7/10] WhatsApp Queue")
        driver.get(f"{BASE_URL}/notifications/whatsapp-queue/")
        time.sleep(2)
        take_screenshot(driver, "07_whatsapp_queue.png")
        
        # 8. Student Management
        print("\n  [8/10] Student Management")
        driver.get(f"{BASE_URL}/secretary/students/")
        time.sleep(2)
        take_screenshot(driver, "08_student_management.png")
        
        # 9. QR Connect
        print("\n  [9/10] QR Connect")
        driver.get(f"{BASE_URL}/qr-connect/")
        time.sleep(2)
        take_screenshot(driver, "09_qr_connect.png")
        
        # 10. Parent Kiosk
        print("\n  [10/10] Parent Kiosk")
        driver.get(f"{BASE_URL}/parent-kiosk/")
        time.sleep(2)
        take_screenshot(driver, "10_parent_kiosk.png")
        
        print("\n" + "=" * 60)
        print("✅ All screenshots generated successfully!")
        print(f"📁 Location: {SCREENSHOTS_DIR}")
        
        # List all screenshots
        print("\n📋 Generated Files:")
        for i, f in enumerate(sorted(SCREENSHOTS_DIR.glob("*.png")), 1):
            size = f.stat().st_size / 1024
            print(f"   {i:02d}. {f.name} ({size:.1f} KB)")
        
    except Exception as e:
        print(f"\n❌ Error generating screenshots: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
    
    return True


if __name__ == "__main__":
    print("\n🔧 Prerequisites:")
    print("  1. Start Django server: python manage.py runserver 0.0.0.0:8000")
    print("  2. Install Selenium: pip install selenium webdriver-manager")
    print("  3. Install Chrome/Chromium browser\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        input("\nPress Enter when server is ready...")
    
    generate_screenshots()
