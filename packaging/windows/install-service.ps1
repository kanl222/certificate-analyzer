[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Проверка прав администратора
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Warning "Для установки службы Windows требуются права администратора."
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
    Write-Error "Python не найден. Убедитесь, что виртуальное окружение .venv создано или Python добавлен в PATH."
    exit 1
}

Write-Host "Используется Python: $PythonExe"

# Проверка наличия модулей win32service
& $PythonExe -c "import win32service, win32serviceutil" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Модуль win32service не найден. Установка пакетов для Windows..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv sync --extra windows
    } else {
        & $PythonExe -m pip install "pywin32>=306" "win10toast>=0.9"
    }
}

Write-Host "==> Регистрация службы Windows CertificateAnalyzer..."
& $PythonExe -m certificate_analyzer service install

if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Запуск службы CertificateAnalyzer..."
    & $PythonExe -m certificate_analyzer service start
    Write-Host "Служба CertificateAnalyzer успешно установлена и запущена."
} else {
    Write-Error "Ошибка при установке службы Windows (код $LASTEXITCODE)."
    exit $LASTEXITCODE
}
