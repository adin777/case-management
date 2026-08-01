$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "apps\api"
$Web = Join-Path $Root "apps\web"
$Python = Join-Path $Api ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local environment is missing. Run scripts\setup-local.ps1 first." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm was not found in PATH. Install Node.js and run setup-local.ps1." }

$ApiProcess = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList "-NoExit", "-Command", "Set-Location '$Api'; & '$Python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
$WebProcess = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList "-NoExit", "-Command", "Set-Location '$Web'; npm run dev -- --host 127.0.0.1 --port 3000"
@{api=$ApiProcess.Id;web=$WebProcess.Id} | ConvertTo-Json | Set-Content (Join-Path $Root "data\local-processes.json")

for ($attempt=0; $attempt -lt 60; $attempt++) {
    try { Invoke-WebRequest "http://localhost:8000/health" -UseBasicParsing | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}
for ($attempt=0; $attempt -lt 60; $attempt++) {
    try { Invoke-WebRequest "http://localhost:3000" -UseBasicParsing | Out-Null; Start-Process "http://localhost:3000"; Write-Host "Case Management is running at http://localhost:3000" -ForegroundColor Green; exit 0 } catch { Start-Sleep -Seconds 1 }
}
throw "The local services did not become ready. Run stop-local.ps1 and inspect the service windows."
