# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller runtime hook for the offline desktop build.

``JDHUB_INSTANCE_DIR`` is the single writable folder that holds the bundled
source *and* the runtime data (``db.sqlite3``, ``media/``, ``backups/``). The
launcher (``main.py``) resolves it from the executable location and writes it
back into the environment before Django is imported; this hook is a safety net
so Django can always find the folder even if it is imported first.
"""
import os
import sys

bundle_dir = getattr(sys, '_MEIPASS', None)
exe_dir = os.path.dirname(sys.executable)

os.environ.setdefault('JDHUB_EDITION', 'offline')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_sms.settings')
os.environ.setdefault('JDHUB_INSTANCE_DIR', exe_dir)
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# The bundled application packages (django_sms, core, ...) live in exe_dir in
# an onedir build; make sure they are importable.
if exe_dir not in sys.path:
    sys.path.insert(0, exe_dir)
if bundle_dir and bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)
