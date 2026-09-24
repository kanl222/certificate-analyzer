$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try { uv run pytest @args; exit $LASTEXITCODE } finally { Pop-Location }
