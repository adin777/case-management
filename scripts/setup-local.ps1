$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "apps\api"
$Web = Join-Path $Root "apps\web"

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $Python) { throw "Python 3.12 or newer is required and was not found in PATH." }

$VenvPython = Join-Path $Api ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { & $Python.Source -m venv (Join-Path $Api ".venv") }
& $VenvPython -m pip install -e "${Api}[dev]"
Push-Location $Api
try {
    & (Join-Path $Api ".venv\Scripts\alembic.exe") upgrade head
    & $VenvPython -m app.seed
} finally { Pop-Location }

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 22 or newer is required and was not found in PATH." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm is required and was not found in PATH." }
Push-Location $Web
try { npm install } finally { Pop-Location }
Write-Host "Setup complete. Run scripts\start-local.ps1 and open http://localhost:3000" -ForegroundColor Green
