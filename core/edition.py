"""Edition / runtime-mode helpers.

The application ships in two editions:

* **offline** – a self-contained desktop/APK build that runs entirely on the
  school's own machine or phone hotspot. It performs no outbound network calls
  and binds the license to the machine's hardware ID (HWID).
* **online** – the original development/server build, which may use cloud
  helpers (Google Drive backup, update checks, ...).

The edition is decided by, in order:

1. the ``JDHUB_EDITION`` environment variable (set by the frozen desktop
   launcher and by the Android wrapper's service),
2. a frozen (PyInstaller) binary, which is always the offline desktop build,
3. the default ``online`` for a normal source checkout.
"""
import os
import sys

VALID_EDITIONS = ('offline', 'online')


def get_edition() -> str:
    """Return the active edition: ``'offline'`` or ``'online'``."""
    explicit = os.environ.get('JDHUB_EDITION', '').strip().lower()
    if explicit in VALID_EDITIONS:
        return explicit
    if getattr(sys, 'frozen', False):
        return 'offline'
    return 'online'


def is_offline() -> bool:
    """True when running the fully offline edition."""
    return get_edition() == 'offline'
