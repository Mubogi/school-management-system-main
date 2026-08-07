; =============================================================================
; JD Hub School Management System - Inno Setup Installer Script
; =============================================================================
; Developer: Jordan Design Hub (JD Hub)
; Contact: +256 754 687 597 | jordandesignhub@gmail.com
; =============================================================================

#define MyAppName "School Management System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Jordan Design Hub (JD Hub)"
#define MyAppURL "https://jordandesignhub.com"
#define MyAppExeName "SchoolSystem.exe"

[Setup]
; Application Info
AppId={{8F5D2C4A-7E3B-4A1D-9E6F-2C8B0A3D5E7F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Contact Information
AppContact=+256 754 687 597
AppEmail=jordandesignhub@gmail.com
AppCopyright=Copyright (C) 2024 Jordan Design Hub (JD Hub). All rights reserved.

; Directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=installer
OutputBaseFilename=JDHub_SchoolManagement_{#MyAppVersion}_Setup
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Appearance
WizardStyle=modern
SetupIconFile=images\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Licensing
LicenseFile=LICENSE.txt
; InfoBeforeFile=README.md

; Versioning
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=School Management System Installer
VersionInfoCopyright=Copyright (C) 2024 Jordan Design Hub (JD Hub)
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Minimum Windows Version
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files from PyInstaller dist folder
Source: "dist\SchoolSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Note: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{group}\JD Hub Website"; Filename: "https://jordandesignhub.com"
Name: "{group}\Contact Support"; Filename: "mailto:jordandesignhub@gmail.com"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Run after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Windows Apps & Features registration
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"

; Add to Windows Apps & Features (Registry manifest for Windows 10/11)
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "UninstallString"; ValueData: "{uninstallexe}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#MyAppVersion}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#MyAppURL}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: string; ValueName: "Contact"; ValueData: "{#MyAppContact}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: dword; ValueName: "NoModify"; ValueData: 1
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: dword; ValueName: "NoRepair"; ValueData: 1
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}"; ValueType: dword; ValueName: "EstimatedSize"; ValueData: 500000

[Code]
// Pascal Script for custom installation logic

var
  ResultCode: Integer;

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Check for Python installation if needed
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks
    // Create data directory if needed
    ForceDirectories(ExpandConstant('{app}\data'));
    ForceDirectories(ExpandConstant('{app}\backups'));
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  // Check if application is running before uninstall
  if CheckForMutexes('{#MyAppName}') then
  begin
    if MsgBox('The application is currently running. Please close it before uninstalling.', mbError, MB_RETRYCANCEL) = IDRETRY then
    begin
      Result := False;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Ask user if they want to keep data
    if MsgBox('Do you want to keep your data files (database, backups)?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Keep data directory
      Log('User chose to keep data files');
    end
    else
    begin
      // Delete data directory
      DelTree(ExpandConstant('{app}\data'), True, True, True);
      DelTree(ExpandConstant('{app}\backups'), True, True, True);
    end;
  end;
end;

// Custom function to check if running as admin
function IsAdminInstallMode(): Boolean;
begin
  Result := IsAdmin();
end;

// Function to get installed size
function GetInstalledSize(): String;
begin
  Result := '500 MB';
end;

[UninstallDelete]
// Clean up installation files
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\temp"

[Messages]
BeveledLabel=Powered by Jordan Design Hub (JD Hub)
SetupWindowTitle=JD Hub School Management System - Setup
UninstallDisplayNameMark={#MyAppName}
UninstallDisplayNameMarks=({#MyAppName})
