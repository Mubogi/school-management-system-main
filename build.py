#!/usr/bin/env python
"""
PyInstaller Build Script for School Management System Desktop Application

This script packages the application as a standalone desktop executable.

Usage:
    # Development build (one-dir)
    python build.py
    
    # Production build
    python build.py --prod
    
    # Clean build
    python build.py --clean

Output:
    Creates a 'dist' directory with the packaged application.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Build configuration
APP_NAME = "SchoolManagementSystem"
MAIN_SCRIPT = "main.py"
ICON_FILE = "images/company-logo.png"  # Optional icon

# Paths
BASE_DIR = Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"

# Hidden imports for Django and other dependencies
HIDDEN_IMPORTS = [
    # Django core
    'django',
    'django.contrib',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.core.cache',
    'django.core.mail',
    'django.core.management',
    'django.core.wsgi',
    
    # Core app
    'core',
    'core.models',
    'core.views',
    'core.forms',
    'core.middleware',
    'core.urls',
    'core.admin',
    
    # Licensing app
    'licensing',
    'licensing.models',
    'licensing.views',
    'licensing.activation',
    'licensing.hwid',
    'licensing.middleware',
    'licensing.decorators',
    
    # School app
    'school',
    'school.models',
    'school.views',
    'school.urls',
    
    # Third party
    'reportlab',
    'PIL',
    'PIL._imaging',
    'weasyprint',
    'qrcode',
    'qrcode.image',
    'cryptography',
    'cffi',
]


def clean():
    """Remove build directories."""
    print("Cleaning build directories...")
    
    for directory in [DIST_DIR, BUILD_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
            print(f"  Removed: {directory}")


def build_spec_file(production=False):
    """Generate PyInstaller spec file content."""
    
    # Determine analysis parameters
    binaries = []
    datas = [
        # Static files
        (str(BASE_DIR / 'core' / 'static'), 'core/static'),
        (str(BASE_DIR / 'school' / 'static'), 'school/static'),
        (str(BASE_DIR / 'css'), 'css'),
        (str(BASE_DIR / 'js'), 'js'),
        (str(BASE_DIR / 'images'), 'images'),
        (str(BASE_DIR / 'staticfiles'), 'staticfiles'),
        
        # Django templates
        (str(BASE_DIR / 'core' / 'templates'), 'core/templates'),
        (str(BASE_DIR / 'school' / 'templates'), 'school/templates'),
        (str(BASE_DIR / 'licensing' / 'templates'), 'licensing/templates'),
        
        # Database
        (str(BASE_DIR / 'db.sqlite3'), '.'),
    ]
    
    # Include additional hidden imports
    hidden_imports_str = '\n    '.join([f"'{imp}'," for imp in HIDDEN_IMPORTS])
    
    # Hidden imports for PyInstaller
    hidden_imports = HIDDEN_IMPORTS
    
    # Console mode (True for debugging)
    console = not production
    
    # Icon path
    icon_path = str(BASE_DIR / ICON_FILE) if Path(ICON_FILE).exists() else ''
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Hidden imports
hiddenimports = [
    {hidden_imports_str}
]

a = Analysis(
    ['{MAIN_SCRIPT}'],
    pathex=['{BASE_DIR}'],
    binaries={binaries},
    datas={datas},
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',  # Exclude if not needed
        'pandas',  # Exclude if not needed
    ],
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
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={console},
    {'icon="' + icon_path + '",' if icon_path else ''}
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    target_directory='{APP_NAME}',
)
'''
    return spec_content


def build(production=False):
    """Run PyInstaller build."""
    
    print(f"\n{'='*60}")
    print(f"Building {APP_NAME} (Production: {production})")
    print(f"{'='*60}\n")
    
    # Generate spec file
    spec_file = BASE_DIR / f"{APP_NAME}.spec"
    spec_content = build_spec_file(production)
    
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print(f"Generated spec file: {spec_file}")
    
    # Build command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--onedir',  # One directory output
        '--clean',
        '--noconfirm',
        str(MAIN_SCRIPT),
    ]
    
    if production:
        cmd.append('--noconsole')
    
    if Path(ICON_FILE).exists():
        cmd.extend(['--icon', ICON_FILE])
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR))
        
        if result.returncode == 0:
            print(f"\n{'='*60}")
            print("BUILD SUCCESSFUL!")
            print(f"{'='*60}")
            print(f"\nOutput directory: {DIST_DIR / APP_NAME}")
            print(f"\nTo run the application:")
            print(f"  {DIST_DIR / APP_NAME / APP_NAME}.exe")
        else:
            print(f"\n{'='*60}")
            print("BUILD FAILED!")
            print(f"{'='*60}")
            return 1
            
    except FileNotFoundError:
        print("\nERROR: PyInstaller not found!")
        print("\nInstall PyInstaller with:")
        print("  pip install pyinstaller")
        return 1
    
    return 0


def install_dependencies():
    """Install required dependencies."""
    
    print("\nInstalling dependencies...")
    
    deps = [
        'pyinstaller',
        'pywebview',
        'django>=4.0',
        'reportlab',
        'Pillow',
        'qrcode',
        'weasyprint',
    ]
    
    for dep in deps:
        print(f"  Installing {dep}...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', dep])
    
    print("Dependencies installed!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Build School Management System Desktop Application'
    )
    parser.add_argument(
        '--clean', '-c',
        action='store_true',
        help='Clean build directories before building'
    )
    parser.add_argument(
        '--prod', '-p',
        action='store_true',
        help='Production build (no console window)'
    )
    parser.add_argument(
        '--install-deps',
        action='store_true',
        help='Install required dependencies'
    )
    
    args = parser.parse_args()
    
    if args.install_deps:
        install_dependencies()
        return
    
    if args.clean:
        clean()
    
    sys.exit(build(args.prod))


if __name__ == '__main__':
    main()
