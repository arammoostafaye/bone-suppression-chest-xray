; BoneSuppression AI - Inno Setup 6 Script
; Generates BoneSuppression_Setup.exe for Windows 10/11 (64-bit)
; Supports offline installations, Persian & English interface, and DICOM association.

#define MyAppName "BoneSuppression AI"
#define MyAppVersion "2.4.1"
#define MyAppPublisher "Aram Mostafaei / Boali Hospital Marivan"
#define MyAppURL "https://github.com/arammoostafaye/bone-suppression-chest-xray"
#define MyAppExeName "BoneSuppressionAI.exe"

[Setup]
AppId={{9B37E49E-4C2E-4F3D-9A4E-7C1268499B82}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=BoneSuppression_v1.0_Windows_Setup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "dicomassoc"; Description: "Associate with DICOM medical images (.dcm)"; GroupDescription: "File Associations"

[Files]
; Standalone compiled files or Python script distribution
Source: "dist\BoneSuppressionAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: HasCompiledExe
Source: "BoneSuppression_Desktop.py"; DestDir: "{app}"; Flags: ignoreversion; Check: not HasCompiledExe
Source: "suppress.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "run_desktop_app.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "download_all_weights.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "weights\*"; DestDir: "{app}\weights"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Check: HasCompiledExe
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\run_desktop_app.bat"; Check: not HasCompiledExe
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Check: HasCompiledExe
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run_desktop_app.bat"; Tasks: desktopicon; Check: not HasCompiledExe

[Registry]
Root: HKA; Subkey: "Software\Classes\.dcm"; ValueType: string; ValueName: ""; ValueData: "BoneSuppression.DICOM"; Flags: uninsdeletevalue; Tasks: dicomassoc
Root: HKA; Subkey: "Software\Classes\BoneSuppression.DICOM"; ValueType: string; ValueName: ""; ValueData: "DICOM Medical Radiograph"; Flags: uninsdeletekey; Tasks: dicomassoc
Root: HKA; Subkey: "Software\Classes\BoneSuppression.DICOM\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: dicomassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent; Check: HasCompiledExe
Filename: "{app}\run_desktop_app.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent; Check: not HasCompiledExe

[Code]
function HasCompiledExe: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\{#MyAppExeName}')) or FileExists(ExtractFilePath(ExpandConstant('{src}')) + 'dist\BoneSuppressionAI\BoneSuppressionAI.exe');
end;
