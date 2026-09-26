[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Проверка прав администратора
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Warning "Для удаления службы Windows требуются права администратора."
    Write-Host "Попытка перезапуска с повышенными привилегиями..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

function Find-Python {
    if ($env:VIRTUAL_ENV -and (Test-Path "$env:VIRTUAL_ENV\Scripts\python.exe")) {
        return "$env:VIRTUAL_ENV\Scripts\python.exe"
    }
    $localVenv = Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe"
    if (Test-Path $localVenv) {
        return (Resolve-Path $localVenv).Path
    }
    $cmdPython = (Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($cmdPython) {
        return $cmdPython.Source
    }
    return $null
}

$PythonExe = Find-Python
if (-not $PythonExe) {
    Write-Error "Python не найден."
    exit 1
}

Write-Host "==> Остановка службы CertificateAnalyzer (если запущена)..."
try {
    & $PythonExe -m certificate_analyzer service stop 2>$null
} catch {
    # Игнорируем ошибку, если служба уже остановлена
}

Write-Host "==> Удаление службы Windows CertificateAnalyzer..."
& $PythonExe -m certificate_analyzer service remove
if ($LASTEXITCODE -eq 0) {
    Write-Host "Служба CertificateAnalyzer успешно удалена."
} else {
    Write-Warning "Код завершения при удалении службы: $LASTEXITCODE"
}
