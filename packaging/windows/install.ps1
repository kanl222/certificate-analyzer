[CmdletBinding()]
param(
    [switch]$NoService,
    [switch]$ServiceOnly,
    [switch]$NoShortcuts,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host @"
Использование: .\install.ps1 [ПАРАМЕТРЫ]

Устанавливает Certificate Analyzer для Windows:
  - Устанавливает зависимости (GUI и компоненты Windows)
  - Создает ярлыки приложения на рабочем столе и в меню 'Пуск'
  - Регистрирует и запускает фоновую службу мониторинга Windows

Параметры:
  -ServiceOnly      Установить только службу Windows (без ярлыков)
  -NoService        Пропустить установку службы Windows (только приложение и ярлыки)
  -NoShortcuts      Не создавать ярлыки на рабочем столе и в меню 'Пуск'
  -Help             Показать эту справку
"@
    exit 0
}

Write-Host "==> Начало установки Certificate Analyzer для Windows..."

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

# 1. Поиск Python и установка зависимостей
function Find-Python {
    if ($env:VIRTUAL_ENV -and (Test-Path "$env:VIRTUAL_ENV\Scripts\python.exe")) {
        return "$env:VIRTUAL_ENV\Scripts\python.exe"
    }
    $localVenv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $localVenv) {
        return (Resolve-Path $localVenv).Path
    }
    $cmdPython = (Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($cmdPython) {
        return $cmdPython.Source
    }
    return $null
}

if (-not $ServiceOnly) {
    Write-Host "==> Проверка и установка пакетов Python..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Push-Location $ProjectRoot
        try {
            & uv sync --extra gui --extra windows
        } finally {
            Pop-Location
        }
    } else {
        $py = Find-Python
        if (-not $py) {
            Write-Error "Не найден Python или uv. Установите Python 3.11+ и добавьте его в PATH."
            exit 1
        }
        Push-Location $ProjectRoot
        try {
            & $py -m pip install -e ".[gui,windows]"
        } finally {
            Pop-Location
        }
    }
}

$PythonExe = Find-Python
if (-not $PythonExe) {
    Write-Error "Не удалось найти исполняемый файл Python."
    exit 1
}

# 2. Создание ярлыков
if (-not $NoShortcuts -and -not $ServiceOnly) {
    Write-Host "==> Создание ярлыков на рабочем столе и в меню 'Пуск'..."
    
    $VenvScripts = Split-Path $PythonExe -Parent
    $CertExe = Join-Path $VenvScripts "certificate-analyzer.exe"
    $TargetExe = if (Test-Path $CertExe) { $CertExe } else { Join-Path $VenvScripts "pythonw.exe" }
    $Arguments = if (Test-Path $CertExe) { "gui" } else { "-m certificate_analyzer gui" }

    $WshShell = New-Object -ComObject WScript.Shell

    # Ярлык на Рабочем столе
    $DesktopPath = [Environment]::GetFolderPath('Desktop')
    $DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "Certificate Analyzer.lnk"))
    $DesktopShortcut.TargetPath = $TargetExe
    $DesktopShortcut.Arguments = $Arguments
    $DesktopShortcut.WorkingDirectory = $ProjectRoot.Path
    $DesktopShortcut.Description = "Анализатор сертификатов X.509 и машиночитаемых доверенностей"
    $DesktopShortcut.Save()
    Write-Host "Ярлык на рабочем столе создан."

    # Ярлык в меню 'Пуск'
    $ProgramsPath = [Environment]::GetFolderPath('Programs')
    if (Test-Path $ProgramsPath) {
        $StartShortcut = $WshShell.CreateShortcut((Join-Path $ProgramsPath "Certificate Analyzer.lnk"))
        $StartShortcut.TargetPath = $TargetExe
        $StartShortcut.Arguments = $Arguments
        $StartShortcut.WorkingDirectory = $ProjectRoot.Path
        $StartShortcut.Description = "Анализатор сертификатов X.509 и машиночитаемых доверенностей"
        $StartShortcut.Save()
        Write-Host "Ярлык в меню 'Пуск' создан."
    }
}

# 3. Установка службы Windows
if (-not $NoService) {
    Write-Host "==> Настройка фоновой службы Windows..."
    $InstallServiceScript = Join-Path $PSScriptRoot "install-service.ps1"
    & $InstallServiceScript
}

Write-Host "==> Установка Certificate Analyzer завершена!"
