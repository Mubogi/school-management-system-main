#!/usr/bin/env python
"""Build the offline desktop edition (Windows/Linux) with PyInstaller.

    python build.py --clean          # clean onedir build
    python build.py --clean --zip    # also produce a portable .zip
    python build.py --installer      # also compile installer_setup.iss (Windows)

Output: dist/JDHubSchoolSystem/
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / 'dist'
BUILD_DIR = BASE_DIR / 'build'
APP_NAME = 'JDHubSchoolSystem'
OUT_DIR = DIST_DIR / APP_NAME
SPEC_FILE = BASE_DIR / 'school_system.spec'

REQUIRED = [
    'Django>=4.2', 'reportlab>=4.0', 'qrcode[pil]>=7.4', 'whitenoise>=6.6',
    'pywebview>=5.0', 'cryptography>=42.0', 'pyinstaller>=6.0', 'pypdf>=4.0',
]


def clean():
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)
            print(f'  removed {d}')


def install_deps():
    for pkg in REQUIRED:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pkg], check=False)


def compile_spec():
    print(f'Running PyInstaller: {SPEC_FILE.name}')
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', str(SPEC_FILE)]
    return subprocess.run(cmd, cwd=str(BASE_DIR)).returncode


def make_zip():
    zip_path = DIST_DIR / f'{APP_NAME}-windows-portable.zip'
    print(f'Zipping portable bundle -> {zip_path.name}')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in OUT_DIR.rglob('*'):
            if file.is_file():
                zf.write(file, file.relative_to(DIST_DIR))
    print(f'  {zip_path} ({zip_path.stat().st_size // (1024 * 1024)} MB)')


def make_installer():
    iss = BASE_DIR / 'installer_setup.iss'
    if not iss.exists():
        print('installer_setup.iss not found')
        return 1
    for candidate in (
        Path(os.environ.get('ProgramFiles(x86)', '')) / 'Inno Setup 6' / 'ISCC.exe',
        Path(os.environ.get('ProgramFiles', '')) / 'Inno Setup 6' / 'ISCC.exe',
    ):
        if candidate.is_file():
            return subprocess.run([str(candidate), str(iss)], cwd=str(BASE_DIR)).returncode
    print('Inno Setup (ISCC.exe) not found; compile installer_setup.iss manually.')
    return 1


def main():
    parser = argparse.ArgumentParser(description='Build the offline desktop edition.')
    parser.add_argument('--clean', '-c', action='store_true')
    parser.add_argument('--install-deps', action='store_true')
    parser.add_argument('--zip', action='store_true', help='Produce a portable .zip')
    parser.add_argument('--installer', action='store_true',
                        help='Compile the Inno Setup installer (Windows).')
    args = parser.parse_args()

    if args.install_deps:
        install_deps()
    if args.clean:
        print('Cleaning...')
        clean()

    if compile_spec() != 0:
        print('BUILD FAILED')
        return 1

    print(f'\nBUILD OK -> {OUT_DIR}')
    exe = OUT_DIR / (APP_NAME + ('.exe' if os.name == 'nt' else ''))
    print(f'Run it with: {exe}')

    if args.zip:
        make_zip()
    if args.installer:
        make_installer()
    return 0


if __name__ == '__main__':
    sys.exit(main())
