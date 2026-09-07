param([int]$IntervalSeconds = 60, [switch]$Once)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "apps/api/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) { throw "Python environment is unavailable" }
do {
    Push-Location (Join-Path $projectRoot "apps/api")
    try { & $python -m app.jobs.sla_tick; if ($LASTEXITCODE) { throw "SLA processing failed" } }
    finally { Pop-Location }
    if (-not $Once) { Start-Sleep -Seconds $IntervalSeconds }
} while (-not $Once)
