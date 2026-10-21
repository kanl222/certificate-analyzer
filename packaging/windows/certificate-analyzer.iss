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
DisableDirPage=auto
UsePreviousAppDir=yes
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
SetupIconFile=..\..\src\certificate_analyzer\assets\app-icon.ico
VersionInfoVersion={#AppVersion}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"; Flags: unchecked
Name: "daemon"; Description: "Запускать фоновый мониторинг при входе пользователя"; GroupDescription: "Фоновый мониторинг:"; Flags: checkedonce

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\..\dist\CertificateAnalyzer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#GuiExeName}"; Parameters: "gui"; WorkingDir: "{app}"; AppUserModelID: "kanl.CertificateAnalyzer"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#GuiExeName}"; Parameters: "gui"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "kanl.CertificateAnalyzer"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CertificateAnalyzer"; ValueData: """{app}\{#GuiExeName}"" worker"; Flags: uninsdeletevalue; Tasks: daemon

[Run]
Filename: "{app}\{#GuiExeName}"; Parameters: "worker"; Flags: runhidden nowait; Tasks: daemon
Filename: "{app}\{#GuiExeName}"; Parameters: "gui"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function StopInstalledDaemon: Boolean;
var
  ResultCode: Integer;
  CliPath: String;
  PowerShellPath: String;
begin
  Result := True;
  CliPath := ExpandConstant('{app}\{#CliExeName}');
  if not FileExists(CliPath) and not FileExists(ExpandConstant('{app}\{#GuiExeName}')) then
    Exit;
  if FileExists(CliPath) then
  begin
    if not Exec(CliPath, 'worker --stop', ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      Result := False;
      Exit;
    end;
    { Older releases returned 2 when the daemon was already stopped. }
    Result := (ResultCode = 0) or (ResultCode = 2);
    if not Result then
      Exit;
  end;

  { The worker uses CertificateAnalyzer.exe. Also require the GUI to close. }
  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  if not Exec(PowerShellPath,
    '-NoProfile -NonInteractive -Command "if (Get-Process -Name ''CertificateAnalyzer'' -ErrorAction SilentlyContinue) { exit 1 }; exit 0"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := False
  else
    Result := ResultCode = 0;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not StopInstalledDaemon then
    Result := 'Не удалось остановить фоновый процесс предыдущей версии. Закройте приложение и повторите установку.';
end;

function InitializeUninstall: Boolean;
begin
  Result := StopInstalledDaemon;
  if not Result then
    MsgBox('Не удалось остановить фоновый процесс. Удаление прервано, чтобы не оставить работающую старую версию.', mbError, MB_OK);
end;
