# -*- mode: python ; coding: utf-8 -*-
"""
Runtime hook for PyInstaller build.
Sets up the environment so Django can find its settings, templates,
and static files inside the frozen application bundle.
"""
import os
import sys


def _setup_frozen_env():
    """Configure Django environment for frozen (PyInstaller) execution."""
    # _MEIPASS is the PyInstaller bundle root (temporary in onefile, real dir in onedir)
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_sms.settings')
    os.environ.setdefault('PYTHONUNBUFFERED', '1')

    # Tell Django where the project root lives so BASE_DIR resolves correctly.
    # In a frozen app, BASE_DIR should point to the directory containing the exe
    # (so db.sqlite3, backups/, media/ are writable next to the executable).
    exe_dir = os.path.dirname(sys.executable)
    os.environ.setdefault('JDHUB_BASE_DIR', exe_dir)

    # Add bundle dir to sys.path so Django app modules are importable
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)


_setup_frozen_env()
