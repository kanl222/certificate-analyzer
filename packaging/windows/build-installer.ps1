[CmdletBinding()]
param(
    [switch]$SkipSync,
    [switch]$BundleOnly
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$SpecFile = Join-Path $PSScriptRoot 'certificate-analyzer.spec'
$InnoScript = Join-Path $PSScriptRoot 'certificate-analyzer.iss'

function Find-InnoCompiler {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    return $candidates | Select-Object -First 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv не найден. Установите uv и повторите сборку.'
}

Push-Location $ProjectRoot
try {
    if (-not $SkipSync) {
        Write-Host '==> Установка зависимостей для сборки...'
        & uv sync --extra gui --extra windows --group packaging
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host '==> Сборка автономного приложения PyInstaller...'
    & uv run --no-sync pyinstaller --noconfirm --clean $SpecFile
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $GuiExecutable = Join-Path $ProjectRoot 'dist\CertificateAnalyzer\CertificateAnalyzer.exe'
    $CliExecutable = Join-Path $ProjectRoot 'dist\CertificateAnalyzer\certificate-analyzer-cli.exe'
    if (-not (Test-Path -LiteralPath $GuiExecutable) -or -not (Test-Path -LiteralPath $CliExecutable)) {
        throw 'PyInstaller не создал ожидаемые исполняемые файлы.'
    }

    if ($BundleOnly) {
        Write-Host "==> Автономное приложение готово: $(Split-Path $GuiExecutable -Parent)"
        exit 0
    }

    $InnoCompiler = Find-InnoCompiler
    if (-not $InnoCompiler) {
        throw 'Компилятор Inno Setup 6 не найден. Установите Inno Setup или запустите сценарий с -BundleOnly.'
    }

    $Version = & uv run --no-sync python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
    if ($LASTEXITCODE -ne 0 -or -not $Version) {
        throw 'Не удалось прочитать версию проекта из pyproject.toml.'
    }

    Write-Host "==> Сборка установщика версии $Version..."
    & $InnoCompiler "/DAppVersion=$Version" $InnoScript
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $Installer = Join-Path $ProjectRoot "dist\installer\CertificateAnalyzer-$Version-Setup.exe"
    if (-not (Test-Path -LiteralPath $Installer)) {
        throw 'Inno Setup не создал ожидаемый установщик.'
    }
    Write-Host "==> Установщик готов: $Installer"
} finally {
    Pop-Location
}
