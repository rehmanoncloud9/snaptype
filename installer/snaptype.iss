; Inno Setup script — compile with ISCC.exe after `python build.py`
#define AppName "SnapType"
#define AppVersion "1.5.0"

[Setup]
AppId={{B4C1D2E0-5A7F-4E5B-9C10-5A3D7E21F001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Abdul Rehman
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SnapType-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\SnapType.exe
WizardStyle=modern

[Files]
Source: "..\dist\SnapType.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SnapType.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\SnapType.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\SnapType.exe"; Description: "Launch SnapType"; Flags: nowait postinstall skipifsilent
