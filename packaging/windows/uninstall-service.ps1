[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $PythonExe) {
    $PreviousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = Join-Path $ProjectRoot 'src'
        & $PythonExe -m certificate_analyzer worker --stop
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось остановить фоновый процесс.' }
    } finally {
        $env:PYTHONPATH = $PreviousPythonPath
    }
}
Remove-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name CertificateAnalyzer -ErrorAction SilentlyContinue
Write-Host 'Автозапуск пользовательского демона отключён.'
