$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try { uv run --extra gui certificate-analyzer @args; exit $LASTEXITCODE } finally { Pop-Location }
