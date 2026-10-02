[CmdletBinding()]
param(
    [switch]$Purge,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host @"
Использование: .\uninstall.ps1 [ПАРАМЕТРЫ]

Удаляет Certificate Analyzer для Windows:
  - Останавливает и удаляет пользовательский демон
  - Удаляет ярлыки с рабочего стола и из меню 'Пуск'
  - Опционально очищает данные и конфигурацию

Параметры:
  -Purge            Удалить также данные и настройки пользователя (%USERPROFILE%\.certificate-analyzer)
  -Help             Показать эту справку
"@
    exit 0
}

Write-Host "==> Начало удаления Certificate Analyzer для Windows..."

# 1. Удаление пользовательского демона
$UninstallServiceScript = Join-Path $PSScriptRoot "uninstall-service.ps1"
if (Test-Path $UninstallServiceScript) {
    try {
        & $UninstallServiceScript
    } catch {
        Write-Warning "Ошибка при удалении демона: $_"
    }
}

# 2. Удаление ярлыков
Write-Host "==> Удаление ярлыков приложения..."

$DesktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) "Certificate Analyzer.lnk"
if (Test-Path $DesktopShortcut) {
    Remove-Item -Force $DesktopShortcut
    Write-Host "Ярлык на рабочем столе удален."
}

$StartShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) "Certificate Analyzer.lnk"
if (Test-Path $StartShortcut) {
    Remove-Item -Force $StartShortcut
    Write-Host "Ярлык в меню 'Пуск' удален."
}

# 3. Очистка пользовательских данных
if ($Purge) {
    $DataDir = Join-Path $env:USERPROFILE ".certificate-analyzer"
    if (Test-Path $DataDir) {
        Write-Host "Удаление данных и конфигурации ($DataDir)..."
        Remove-Item -Recurse -Force $DataDir
        Write-Host "Данные успешно удалены."
    }
}

Write-Host "==> Удаление Certificate Analyzer завершено!"
