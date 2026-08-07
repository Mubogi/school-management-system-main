#!/usr/bin/env python
"""
Desktop Application Entry Point
Uses pywebview to serve the Django app in a native desktop window.

Run this file directly to launch the desktop application:
    python main.py

Or build with PyInstaller using:
    python build.py
"""
import os
import sys
import threading
import webbrowser
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SchoolManagementDesktop')

# Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_sms.settings')

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


def main():
    """
    Main entry point for the desktop application.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='School Management System Desktop Application'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to run the server on (default: 8000)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
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
    
    args = parser.parse_args()
    
    url = f"http://{args.host}:{args.port}"
    
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
            
            # Create pywebview window
            window = webview.create_window(
                title='School Management System',
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
