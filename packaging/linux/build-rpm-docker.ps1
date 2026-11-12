<#
.SYNOPSIS
    Сборка RPM-пакета для ALT Linux внутри официального контейнера Docker.
.DESCRIPTION
    Использует образ registry.altlinux.org/p10/alt для сборки бинарных файлов
    с целевой версией glibc и формирования RPM-пакета для ALT Linux.
.EXAMPLE
    .\packaging\linux\build-rpm-docker.ps1
#>

[CmdletBinding()]
param(
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path "$scriptDir\..\..").Path
$dockerfile = Join-Path $scriptDir "Dockerfile.alt"

# Проверка наличия Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker не найден. Установите Docker Desktop или добавьте docker.exe в PATH."
    exit 1
}

# Проверка работы демона Docker
Write-Host "==> Проверка статуса Docker daemon..." -ForegroundColor Cyan
$dockerStatus = docker info --format '{{.ServerVersion}}' 2>$null
if (-not $dockerStatus) {
    Write-Warning "Docker daemon не запущен."
    $dockerDesktopExe = "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"
    if (Test-Path $dockerDesktopExe) {
        Write-Host "Попытка запуска Docker Desktop ($dockerDesktopExe)..." -ForegroundColor Yellow
        Start-Process $dockerDesktopExe
        Write-Host "Ожидание готовности Docker daemon (до 60 секунд)..." -ForegroundColor Yellow
        $timeout = 60
        $started = $false
        for ($i = 0; $i -lt $timeout; $i += 3) {
            Start-Sleep -Seconds 3
            $dockerStatus = docker info --format '{{.ServerVersion}}' 2>$null
            if ($dockerStatus) {
                $started = $true
                break
            }
        }
        if (-not $started) {
            Write-Error "Docker daemon не ответил за отведенное время. Запустите Docker Desktop вручную и повторите попытку."
            exit 1
        }
    } else {
        Write-Error "Запустите Docker Desktop и повторите попытку."
        exit 1
    }
}

Write-Host "==> Docker daemon активен (версия: $dockerStatus)" -ForegroundColor Green

# Сборка сборочного образа
$imageTag = "certificate-analyzer-builder:alt"
Write-Host "==> Сборка Docker-образа ($imageTag)..." -ForegroundColor Cyan
$buildArgs = @("build", "-f", $dockerfile, "-t", $imageTag)
if ($NoCache) {
    $buildArgs += "--no-cache"
}
$buildArgs += $projectRoot

& docker @buildArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ошибка при сборке сборочного Docker-образа."
    exit $LASTEXITCODE
}

# Запуск сборки RPM внутри контейнера
Write-Host "==> Запуск сборки RPM для ALT Linux в контейнере..." -ForegroundColor Cyan
& docker run --rm -v "${projectRoot}:/workspace" $imageTag
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ошибка при сборке RPM внутри контейнера."
    exit $LASTEXITCODE
}

# Проверка созданного пакета
$distDir = Join-Path $projectRoot "dist\linux"
$packages = Get-ChildItem -Path $distDir -Filter "*-alt1*.rpm" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*debuginfo*" } | Sort-Object LastWriteTime -Descending
if ($packages) {
    $pkg = $packages[0]
    $sizeMb = [math]::Round($pkg.Length / 1MB, 2)
    Write-Host "`n[УСПЕХ] Сборка RPM для ALT Linux завершена успешно!" -ForegroundColor Green
    Write-Host "Файл: $($pkg.FullName) ($sizeMb МБ)" -ForegroundColor Green
} else {
    Write-Warning "RPM-пакет не найден в $distDir"
}
