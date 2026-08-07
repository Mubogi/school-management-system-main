#!/usr/bin/env python
"""
JD Hub School Management System - Desktop Application Entry Point
Uses pywebview to serve the Django app in a native desktop window.

Run this file directly to launch the desktop application:
    python main.py

Or build with PyInstaller using:
    python build.py

Developer: Jordan Design Hub (JD Hub)
Contact: +256 754 687 597 | jordandesignhub@gmail.com
"""
import os
import sys
import threading
import webbrowser
import logging
import shutil
import atexit
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('JDHubSchoolSystem')

# App Info
APP_NAME = "JD Hub School Management System"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "Jordan Design Hub (JD Hub)"
APP_CONTACT = "+256 754 687 597"
APP_EMAIL = "jordandesignhub@gmail.com"

# Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_sms.settings')


def create_auto_backup():
    """
    Create an automatic database backup on app exit.
    Called when the application closes.
    """
    try:
        from django.conf import settings
        
        db_path = settings.DATABASES['default']['NAME']
        
        if not os.path.exists(db_path):
            logger.warning("Database file not found, skipping backup")
            return
        
        # Create backups directory
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'auto_backup_{timestamp}.sqlite3'
        backup_path = os.path.join(backup_dir, backup_name)
        
        # Copy database
        shutil.copy2(db_path, backup_path)
        
        logger.info(f"Auto-backup created: {backup_name}")
        
        # Keep only last 5 auto backups to save space
        import glob
        auto_backups = sorted(glob.glob(os.path.join(backup_dir, 'auto_backup_*.sqlite3')))
        while len(auto_backups) > 5:
            oldest = auto_backups.pop(0)
            os.remove(oldest)
            logger.info(f"Removed old auto-backup: {os.path.basename(oldest)}")
        
    except Exception as e:
        logger.error(f"Auto-backup failed: {e}")


def start_django_server(host='127.0.0.1', port=8000):
    """
    Start Django development server in a background thread.
    Returns the server URL once ready.
    """
    import time
    import django
    from django.core.management import execute_from_command_line
    
    # Setup Django
    django.setup()
    
    logger.info(f"Starting Django server on {host}:{port}")
    
    # Start the server
    from django.core.management.commands.runserver import Command as RunServerCommand
    from django.conf import settings
    
    # Create a simple HTTP server that Django can use
    from wsgiref.simple_server import make_server, WSGIServer
    from django.core.wsgi import get_wsgi_application
    
    application = get_wsgi_application()
    httpd = make_server(host, port, application)
    
    logger.info(f"Server running at http://{host}:{port}")
    logger.info("Press Ctrl+C to stop the server")
    
    # Serve until stopped
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        httpd.shutdown()


def open_browser(url, delay=2):
    """Open the browser after a short delay."""
    import time
    time.sleep(delay)
    webbrowser.open(url)


def print_banner():
    """Print application banner."""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗██╗  ██╗ ██████╗ ██████╗                         ║
║   ██╔════╝██║ ██╔╝██╔═══██╗██╔══██╗                        ║
║   ███████╗█████╔╝ ██║   ██║██████╔╝                        ║
║   ╚════██║██╔═██╗ ██║   ██║██╔══██╗                        ║
║   ███████║██║  ██╗╚██████╔╝██║  ██║                        ║
║   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝                        ║
║                                                              ║
║   SCHOOL MANAGEMENT SYSTEM                                    ║
║   Version {APP_VERSION}                                              ║
║                                                              ║
║   Powered by Jordan Design Hub (JD Hub)                      ║
║   Contact: {APP_CONTACT}                              ║
║   Email: {APP_EMAIL}                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """
    Main entry point for the desktop application.
    """
    import argparse
    
    # Print banner
    print_banner()
    
    parser = argparse.ArgumentParser(
        description=f'{APP_NAME} - Powered by {APP_PUBLISHER}'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to run the server on (default: 8000)'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 for LAN access)'
    )
    parser.add_argument(
        '--browser', '-b',
        action='store_true',
        help='Open system browser instead of using webview'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Disable auto-backup on close'
    )
    
    args = parser.parse_args()
    
    # Register auto-backup hook (unless disabled)
    if not args.no_backup:
        atexit.register(create_auto_backup)
        logger.info("Auto-backup on close enabled")
    
    url = f"http://{args.host}:{args.port}"
    
    logger.info(f"Starting {APP_NAME}")
    logger.info(f"Bind address: {args.host}:{args.port}")
    
    if args.browser:
        # Run without webview - just use browser
        logger.info(f"Starting server at {url}")
        os.environ['DEBUG'] = 'True' if args.debug else 'False'
        start_django_server(args.host, args.port)
    else:
        # Try to use pywebview
        try:
            import webview
            
            logger.info("Initializing desktop window...")
            
            # Start Django server in background thread
            server_thread = threading.Thread(
                target=start_django_server,
                args=(args.host, args.port),
                daemon=True
            )
            server_thread.start()
            
            # Wait for server to start
            import time
            time.sleep(2)
            
            # Create pywebview window with JD Hub branding
            window = webview.create_window(
                title=f'{APP_NAME} - Powered by JD Hub',
                url=url,
                width=1280,
                height=800,
                min_size=(800, 600),
                resizable=True,
                js_api=None,
            )
            
            # Start webview
            webview.start()
            
        except ImportError:
            logger.warning(
                "pywebview not installed. "
                "Install it with: pip install pywebview\n"
                "Falling back to browser mode..."
            )
            
            # Fallback to browser mode
            browser_thread = threading.Thread(
                target=open_browser,
                args=(url, 2),
                daemon=True
            )
            browser_thread.start()
            
            start_django_server(args.host, args.port)


if __name__ == '__main__':
    main()
