; =============================================================================
; JD Hub School Management System - Inno Setup script (offline edition)
; =============================================================================
; Compile with Inno Setup 6 (ISCC.exe installer_setup.iss) after running
;   python build.py --clean
; The PyInstaller bundle is copied from dist\JDHubSchoolSystem\.
; =============================================================================

#define MyAppName "JD Hub School Management System"
#define MyAppVersion "1.3.1"
#define MyAppPublisher "Jordan Design Hub (JD Hub)"
#define MyAppURL "https://jordandesignhub.com"
#define MyAppExeName "JDHubSchoolSystem.exe"
#define MyAppContact "+256 754 687 597"

[Setup]
AppId={{8F5D2C4A-7E3B-4A1D-9E6F-2C8B0A3D5E7F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppContact={#MyAppContact}
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir=installer
OutputBaseFilename=JDHub_SchoolManagement_Offline_{#MyAppVersion}_Setup
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

WizardStyle=modern
SetupIconFile=images\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

LicenseFile=LICENSE.txt

VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=JD Hub School Management System (Offline Edition)
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\JDHubSchoolSystem\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{group}\Contact Support"; Filename: "mailto:jordandesignhub@gmail.com"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[Registry]
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; \
    ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\app.log"

[Code]
// The app keeps its database, media and backups under the user's
// %LOCALAPPDATA%\JDHubSchoolSystem folder (an installed copy under
// Program Files is read-only for normal users). A per-user copy created on a
// previous run may also exist beside the executable for portable installs.
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    ForceDirectories(ExpandConstant('{localappdata}\JDHubSchoolSystem\media'));
    ForceDirectories(ExpandConstant('{localappdata}\JDHubSchoolSystem\backups'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox('Keep your school data (database, media, backups)?',
              mbConfirmation, MB_YESNO) = IDNO then
    begin
      // Data written next to the executable (portable installs).
      DelTree(ExpandConstant('{app}\db.sqlite3'), False, True, False);
      DelTree(ExpandConstant('{app}\media'), True, True, True);
      DelTree(ExpandConstant('{app}\backups'), True, True, True);
      // Data written under %LOCALAPPDATA% (normal installed copies).
      DelTree(ExpandConstant('{localappdata}\JDHubSchoolSystem'), True, True, True);
    end;
  end;
end;
