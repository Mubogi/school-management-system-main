@echo off
REM ===========================================================================
REM  JD Hub School Management System - offline edition, Windows build
REM  Run this on a Windows PC with Python 3.11+ installed.
REM ===========================================================================
setlocal

echo.
echo ============================================================
echo   Building JD Hub School Management System (Offline Edition)
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.11+ first.
    pause
    exit /b 1
)

echo [1/3] Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo [2/3] Running unit checks before packaging...
python manage.py check || goto :failed

echo.
echo [3/3] Packaging with PyInstaller...
python build.py --clean --zip || goto :failed

echo.
echo ============================================================
echo   BUILD COMPLETE
echo ============================================================
echo   Executable : dist\JDHubSchoolSystem\JDHubSchoolSystem.exe
echo   Portable   : dist\JDHubSchoolSystem-windows-portable.zip
echo.
echo   To build the installer, open installer_setup.iss with Inno Setup 6.
echo   (or run: python build.py --installer)
echo.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
