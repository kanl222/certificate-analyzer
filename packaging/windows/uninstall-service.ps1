[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Remove-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name CertificateAnalyzer -ErrorAction SilentlyContinue
$PythonExe = Join-Path $PSScriptRoot '..\..\.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $PythonExe) { & $PythonExe -m certificate_analyzer worker --stop }
Write-Host 'Автозапуск пользовательского демона отключён.'
