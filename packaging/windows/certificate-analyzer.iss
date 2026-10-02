#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "Certificate Analyzer"
#define AppPublisher "kanl"
#define GuiExeName "CertificateAnalyzer.exe"
#define CliExeName "certificate-analyzer-cli.exe"

[Setup]
AppId={{C0AC7EF0-FA25-4DF7-B28D-460C1464E482}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Certificate Analyzer
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=CertificateAnalyzer-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#GuiExeName}
VersionInfoVersion={#AppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"; Flags: unchecked
Name: "daemon"; Description: "Запускать фоновый мониторинг при входе пользователя"; GroupDescription: "Фоновый мониторинг:"; Flags: checkedonce

[Files]
Source: "..\..\dist\CertificateAnalyzer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#GuiExeName}"; Parameters: "gui"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#GuiExeName}"; Parameters: "gui"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CertificateAnalyzer"; ValueData: """{app}\{#GuiExeName}"" worker"; Flags: uninsdeletevalue; Tasks: daemon

[Run]
Filename: "{app}\{#GuiExeName}"; Parameters: "worker"; Flags: runhidden nowait; Tasks: daemon
Filename: "{app}\{#GuiExeName}"; Parameters: "gui"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#CliExeName}"; Parameters: "worker --stop"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "StopCertificateAnalyzerDaemon"
