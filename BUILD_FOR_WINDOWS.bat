@echo off
echo ================================================
echo   JD Hub School Management System
echo   Building Windows Executable
echo ================================================
echo.

echo Step 1: Installing PyInstaller...
python -m pip install pyinstaller

echo.
echo Step 2: Building executable...
python -m PyInstaller --clean --noconfirm school_system.spec

echo.
echo ================================================
echo   BUILD COMPLETE!
echo ================================================
echo.
echo Your executable is in:
echo   dist\JDHubSchoolSystem\JDHubSchoolSystem.exe
echo.
echo To create installer, open installer_setup.iss 
echo with Inno Setup Compiler.
echo.
pause
