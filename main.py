#!/usr/bin/env python
"""JD Hub School Management System - offline desktop launcher.

Starts the Django application on ``127.0.0.1`` (plus the LAN interface so
phones on the same hotspot can scan the QR code) and shows it in a native
window. Everything runs locally: no internet connection is required, and the
license is bound to this machine's hardware ID.

Run from source:
    python main.py

Package with:
    python build.py            # PyInstaller onedir bundle
    (then compile installer_setup.iss with Inno Setup)
"""
import argparse
import atexit
import json
import logging
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from wsgiref.simple_server import WSGIServer

# The offline desktop build never talks to the cloud.
os.environ.setdefault('JDHUB_EDITION', 'offline')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_sms.settings')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('JDHubSchoolSystem')

APP_NAME = "JD Hub School Management System"
APP_VERSION = "1.1.0"
APP_PUBLISHER = "Jordan Design Hub (JD Hub)"
APP_CONTACT = "+256 754 687 597"
APP_EMAIL = "jordandesignhub@gmail.com"

DEFAULT_PORT = 8000
_STATE_FILE = 'app_state.json'
_INSTANCE_LOCK = None


def _instance_dir() -> Path:
    """Directory that holds the writable runtime data.

    A program installed under ``C:\\Program Files`` cannot write next to its
    executable (standard users are denied there), which used to make the app
    exit silently on first launch. So when the folder beside the executable is
    not writable we fall back to a per-user location
    (``%LOCALAPPDATA%\\JDHubSchoolSystem``). Portable copies run from a
    writable folder still keep their data beside the executable.
    """
    override = os.environ.get('JDHUB_INSTANCE_DIR', '').strip()
    if override:
        return Path(override).resolve()

    if getattr(sys, 'frozen', False):
        candidate = Path(sys.executable).resolve().parent
    else:
        candidate = Path(__file__).resolve().parent

    if _is_writable(candidate):
        return candidate
    return _user_data_dir()


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / '.write_test'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
        return True
    except OSError:
        return False


def _user_data_dir() -> Path:
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
    if base:
        target = Path(base) / 'JDHubSchoolSystem'
    else:
        target = Path.home() / '.jdhub-school'
    target.mkdir(parents=True, exist_ok=True)
    return target


# ---------------------------------------------------------------------------
# Single-instance guard: a portable app must not run twice against the same
# SQLite file, which would corrupt it.
# ---------------------------------------------------------------------------
def acquire_single_instance_lock(instance: Path) -> bool:
    """Take an exclusive advisory lock on a file in the instance folder.

    The OS releases the lock automatically when the process exits (even on a
    crash), so a stale lock file never blocks a legitimate restart.
    """
    global _INSTANCE_LOCK
    lock_path = instance / '.instance.lock'
    try:
        handle = open(lock_path, 'w')
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _INSTANCE_LOCK = handle
        return True
    except OSError:
        return False


def _port_is_our_app(host: str, port: int) -> bool:
    """Best-effort check whether the app is already serving on the port."""
    import urllib.request
    try:
        with urllib.request.urlopen(f'http://{host}:{port}/accounts/login/', timeout=1.5) as r:
            return r.status < 500
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Backup-on-exit
# ---------------------------------------------------------------------------
def create_auto_backup():
    try:
        from django.conf import settings
        db_path = settings.DATABASES['default']['NAME']
        if not os.path.exists(db_path):
            return
        backup_dir = Path(settings.DATA_DIR) / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(db_path, backup_dir / f'auto_backup_{stamp}.sqlite3')
        logger.info("Auto-backup created")

        import glob
        kept = sorted(glob.glob(str(backup_dir / 'auto_backup_*.sqlite3')))
        for old in kept[:-5]:
            try:
                os.remove(old)
            except OSError:
                pass
    except Exception as exc:  # never block shutdown on a backup failure
        logger.warning(f"Auto-backup skipped: {exc}")


# ---------------------------------------------------------------------------
# First-run preparation
# ---------------------------------------------------------------------------
def prepare_instance():
    """Make sure the writable instance folder and schema are ready."""
    instance = _instance_dir()
    for sub in ('media', 'backups'):
        try:
            (instance / sub).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    os.environ.setdefault('JDHUB_INSTANCE_DIR', str(instance))
    return instance


def setup_file_logging(instance: Path):
    """Mirror logs to a file: a windowed build has no console to show them on."""
    try:
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            instance / 'app.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
    except OSError:
        pass


def ensure_database():
    """Run migrations and seed the first superuser on a fresh install.

    Raises on failure so the caller can surface it; a half-prepared database
    must not start a server nobody can log in to.
    """
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)
    from core.startup import seed_superuser_if_empty
    created = seed_superuser_if_empty()
    logger.info("Database ready")
    return created


def _write_state(port: int, instance: Path):
    try:
        (instance / _STATE_FILE).write_text(json.dumps({
            'version': APP_VERSION,
            'port': port,
            'pid': os.getpid(),
            'started_at': datetime.now().isoformat(timespec='seconds'),
        }, indent=2), encoding='utf-8')
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
class ThreadingWSGIServer(WSGIServer):
    """wsgiref server that handles each request in its own thread so several
    browsers/phones can load pages at the same time."""
    daemon_threads = True

    def process_request(self, request, client_address):
        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address))
        t.daemon = True
        t.start()

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def start_django_server(host: str, port: int):
    import django
    django.setup()
    from wsgiref.simple_server import make_server
    from django.core.wsgi import get_wsgi_application

    logger.info(f"Serving on http://{host}:{port}")
    httpd = make_server(host, port, get_wsgi_application(),
                        server_class=ThreadingWSGIServer)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def _show_fatal(message: str):
    """Make a startup failure visible: a windowed build has no console, so a
    silent exit is what the user would otherwise see."""
    logger.error(message)
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, message)
        root.destroy()
    except Exception:
        pass


def _setup_crash_reporting(instance: Path):
    def _hook(exc_type, exc, tb):
        import traceback
        text = ''.join(traceback.format_exception(exc_type, exc, tb))
        logger.error("Unhandled error:\n%s", text)
        _show_fatal(f"The application hit an unexpected error.\n\n{exc}\n\n"
                    f"Details were written to:\n{instance / 'app.log'}")

    sys.excepthook = _hook


def _set_windows_app_id():
    """Group the taskbar button under our own icon rather than 'python'."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'JordanDesignHub.JDHubSchoolSystem')
    except Exception:
        pass


def get_lan_ip() -> str:
    """Local IP for phone access; no external network required."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    """Poll the port until the app answers or the timeout elapses."""
    import urllib.request
    deadline = time.time() + timeout
    url = f'http://{host}:{port}/accounts/login/'
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                if r.status < 500:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def open_browser(url: str, delay: float = 2.5):
    time.sleep(delay)
    webbrowser.open(url)


def print_banner(instance: Path, port: int, seeded_user=None):
    lan = get_lan_ip()
    creds = ''
    if seeded_user is not None:
        creds = f"""
   First-run login (change it after signing in):
     Username: {seeded_user.username}
     Password: 20020120
"""
    print(f"""
+--------------------------------------------------------------+
|   JD HUB SCHOOL MANAGEMENT SYSTEM  (Offline Edition)         |
|   Version {APP_VERSION}                                             |
+--------------------------------------------------------------+
|   Local : http://127.0.0.1:{port}
|   Phones: http://{lan}:{port}  (same Wi-Fi / hotspot)
|   Data  : {str(instance)[:50]}
+--------------------------------------------------------------+{creds}
""")


def main():
    parser = argparse.ArgumentParser(description=f'{APP_NAME} (Offline Edition)')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT)
    parser.add_argument('--host', default='0.0.0.0',
                        help='Bind address (default: 0.0.0.0 for LAN access)')
    parser.add_argument('--browser', '-b', action='store_true',
                        help='Use the system browser instead of a native window.')
    parser.add_argument('--no-backup', action='store_true')
    parser.add_argument('--no-window', action='store_true',
                        help='Run headless (server only).')
    args = parser.parse_args()

    instance = prepare_instance()
    setup_file_logging(instance)
    _setup_crash_reporting(instance)
    _set_windows_app_id()

    if not acquire_single_instance_lock(instance):
        if _port_is_our_app('127.0.0.1', args.port):
            logger.warning("App already running - opening the existing instance.")
            webbrowser.open(f'http://127.0.0.1:{args.port}')
            return 0
        _show_fatal(
            f"Port {args.port} is already in use by another program.\n\n"
            f"Close the other program, or start this one on a different port:\n"
            f"    JDHubSchoolSystem.exe --port 8010")
        return 1

    try:
        seeded_user = ensure_database()
    except Exception as exc:
        _show_fatal(
            f"Could not prepare the database.\n\n{exc}\n\n"
            f"Log file: {instance / 'app.log'}")
        return 1

    _write_state(args.port, instance)
    print_banner(instance, args.port, seeded_user)

    if not args.no_backup:
        atexit.register(create_auto_backup)

    url = f'http://127.0.0.1:{args.port}'

    server_thread = threading.Thread(
        target=start_django_server, args=(args.host, args.port), daemon=True
    )
    server_thread.start()

    # Wait for the server to accept connections; if it never does, show why
    # instead of opening a window on a dead port.
    if not _wait_for_server('127.0.0.1', args.port, timeout=15):
        _show_fatal(
            f"The web server did not start on port {args.port}.\n\n"
            f"Another program may be using the port. Try:\n"
            f"    JDHubSchoolSystem.exe --port 8010\n\n"
            f"Log file: {instance / 'app.log'}")
        return 1

    if args.no_window:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    if args.browser:
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    try:
        import webview
        webview.create_window(
            title=APP_NAME,
            url=url,
            width=1280,
            height=820,
            min_size=(900, 600),
            resizable=True,
        )
        webview.start()  # blocks until the window is closed
        return 0
    except ImportError:
        logger.warning("pywebview not available - falling back to the browser.")
    except Exception as exc:
        logger.warning(f"Native window failed ({exc}) - using the browser.")

    threading.Thread(target=open_browser, args=(url, 1.0), daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    sys.exit(main())
