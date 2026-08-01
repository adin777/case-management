$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Database = Join-Path $Root "data\case_management.db"
$Answer = Read-Host "Delete the development database and recreate it? Type RESET to continue"
if ($Answer -ne "RESET") { Write-Host "Reset cancelled."; exit 0 }
if (Test-Path $Database) { Remove-Item -LiteralPath $Database }
Push-Location (Join-Path $Root "apps\api")
try {
    & ".\.venv\Scripts\alembic.exe" upgrade head
    & ".\.venv\Scripts\python.exe" -m app.seed
} finally { Pop-Location }
Write-Host "Development database recreated and seeded." -ForegroundColor Green
