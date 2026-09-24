$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '../..')
try { uv build; exit $LASTEXITCODE } finally { Pop-Location }
