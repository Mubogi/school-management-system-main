"""On-device entry point for the offline Android app.

Runs the full Django application (the same code as the desktop edition) inside
the phone and serves it on 127.0.0.1 so the WebView can display it. No internet
and no separate server are required: the school's data lives in a SQLite file
on the phone.

Java calls ``app.start()`` once and then loads http://127.0.0.1:<port>/.
"""
import os
import socket
import sys
import threading
import traceback

_SERVER = None
_STARTED = False
_ERROR = ''
_PORT = 0


def _pick_port(preferred=8765):
    for port in range(preferred, preferred + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return preferred


def _instance_dir():
    """A writable folder for the database, media and backups."""
    prop = _java_property('jdhub.datadir')
    base = prop or os.environ.get('ANDROID_PRIVATE') or os.environ.get('ANDROID_APP_DATA') \
        or os.environ.get('ANDROID_DATA') or os.path.expanduser('~')
    target = os.path.join(base, 'jdhub')
    os.makedirs(target, exist_ok=True)
    return target


def _bundle_dir():
    """The extracted project tree (source, templates, static) set by Java."""
    prop = _java_property('jdhub.bundledir')
    if prop and os.path.isdir(prop):
        return prop
    return None


def _java_property(name):
    """Read a Java system property from the embedded interpreter."""
    try:
        from java.lang import System
        return System.getProperty(name)
    except Exception:
        return None


def _serve(app, port):
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIServer, make_server

    class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True
        allow_reuse_address = True

    global _SERVER
    _SERVER = make_server('127.0.0.1', port, app, server_class=ThreadingWSGIServer)
    _SERVER.serve_forever()


def start():
    """Start the on-device server. Returns the port to load, or 0 on failure."""
    global _STARTED, _ERROR, _PORT

    if _STARTED:
        return _PORT

    try:
        instance = _instance_dir()
        bundle = _bundle_dir()

        os.environ['JDHUB_EDITION'] = 'offline'
        os.environ['JDHUB_INSTANCE_DIR'] = instance
        os.environ['DJANGO_SETTINGS_MODULE'] = 'django_sms.settings'
        os.environ['JDHUB_ANDROID'] = '1'
        if bundle:
            os.environ['JDHUB_BUNDLE_DIR'] = bundle
            if bundle not in sys.path:
                sys.path.insert(0, bundle)

        import django
        django.setup()

        from django.core.management import call_command
        call_command('migrate', interactive=False, verbosity=0)

        try:
            from core.startup import seed_superuser_if_empty
            seed_superuser_if_empty()
        except Exception:
            pass

        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()

        _PORT = _pick_port()
        thread = threading.Thread(target=_serve, args=(application, _PORT), daemon=True)
        thread.start()

        # Wait until the socket accepts connections.
        import time
        import urllib.request
        url = 'http://127.0.0.1:%d/accounts/login/' % _PORT
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=2).read(1)
                break
            except Exception:
                time.sleep(0.5)

        _STARTED = True
        return _PORT
    except Exception:
        _ERROR = traceback.format_exc()
        return 0


def base_url():
    return 'http://127.0.0.1:%d' % _PORT if _PORT else ''


def hwid():
    try:
        from licensing.hwid import _get_hardware_id
        return _get_hardware_id()
    except Exception:
        return ''


def last_error():
    return _ERROR
