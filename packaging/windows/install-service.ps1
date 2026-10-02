[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Создайте окружение .venv перед настройкой автозапуска.' }
& $PythonExe -m certificate_analyzer autostart enable
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$PythonWindowless = Join-Path (Split-Path $PythonExe) 'pythonw.exe'
Start-Process -FilePath $PythonWindowless -ArgumentList '-m certificate_analyzer worker' -WorkingDirectory $ProjectRoot -WindowStyle Hidden
Write-Host 'Демон запускается от текущего пользователя. Автозапуск при входе включён.'
