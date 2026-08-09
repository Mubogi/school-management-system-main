# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for JD Hub School Management System (onedir build).

Build:
    pyinstaller --noconfirm school_system.spec
or:
    python build.py --clean

Output: dist/JDHubSchoolSystem/  (one-directory bundle)
"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# --- Dynamically collect all Django submodules so nothing is missed ---
django_hidden = collect_submodules('django')
project_hidden = collect_submodules('django_sms') + collect_submodules('core') \
    + collect_submodules('school') + collect_submodules('licensing') \
    + collect_submodules('notifications') + collect_submodules('backups') \
    + collect_submodules('utils')
# Third-party libraries with dynamic submodules
thirdparty_hidden = collect_submodules('whitenoise') + collect_submodules('reportlab') \
    + collect_submodules('qrcode') + collect_submodules('PIL') \
    + collect_submodules('pywebview')

hiddenimports = list(set(
    django_hidden + project_hidden + thirdparty_hidden + [
        'sqlite3',
        'PIL._imaging',
        'reportlab',
        'reportlab.platypus',
        'qrcode',
        'qrcode.image',
        'qrcode.image.svg',
        'whitenoise',
        'whitenoise.middleware',
        'cryptography',
        'pywebview',
        'pywebview.platforms',
    ]
))

# --- Data files: templates, static assets, migrations, version info ---
datas = []
datas += collect_data_files('core', include_py_files=False)
datas += collect_data_files('school', include_py_files=False)
datas += collect_data_files('licensing', include_py_files=False)
datas += collect_data_files('notifications', include_py_files=False)

# Explicit template / static directories (recursive)
BASE = os.path.abspath(os.path.dirname(SPEC))
for src, dst in [
    ('core/templates', 'core/templates'),
    ('school/templates', 'school/templates'),
    ('licensing/templates', 'licensing/templates'),
    ('notifications/templates', 'notifications/templates'),
    ('core/static', 'core/static'),
    ('school/static', 'school/static'),
    ('staticfiles', 'staticfiles'),
    ('images', 'images'),
    ('css', 'css'),
    ('js', 'js'),
]:
    src_abs = os.path.join(BASE, src)
    if os.path.isdir(src_abs):
        datas.append((src_abs, dst))

# Ship the version_info.txt (used by Windows exe metadata)
vi = os.path.join(BASE, 'version_info.txt')
if os.path.isfile(vi):
    datas.append((vi, '.'))

# Exclude user-data / generated files that must NOT ship inside the bundle
# (they are created at runtime in DATA_DIR next to the executable).
_EXCLUDE_NAMES = {'db.sqlite3', 'db.sqlite3-journal', 'media', 'backups'}
datas = [
    (src, dst) for src, dst in datas
    if os.path.basename(src.rstrip(os.sep)) not in _EXCLUDE_NAMES
    and not src.endswith(('.sqlite3', '.sqlite3-journal', '.log'))
]

a = Analysis(
    ['main.py'],
    pathex=[BASE],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(BASE, 'school_system_rt_hook.py')],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JDHubSchoolSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BASE, 'images', 'company-logo.png') if os.path.isfile(os.path.join(BASE, 'images', 'company-logo.png')) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JDHubSchoolSystem',
)

