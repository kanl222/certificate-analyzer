$ErrorActionPreference = 'Stop'
# Run from an elevated shell, with the package and its windows extra installed.
python -m certificate_analyzer service install
exit $LASTEXITCODE
