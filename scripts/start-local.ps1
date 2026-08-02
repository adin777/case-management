$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "apps\api"
$Web = Join-Path $Root "apps\web"
$Python = Join-Path $Api ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local environment is missing. Run scripts\setup-local.ps1 first." }
$NodeCommand = Get-Command node -ErrorAction SilentlyContinue
$Node = if ($NodeCommand) { $NodeCommand.Source } else { Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" }
if (-not (Test-Path $Node)) { throw "Node.js was not found. Install Node.js and run setup-local.ps1." }
$Vite = Join-Path $Web "node_modules\vite\bin\vite.js"
if (-not (Test-Path $Vite)) { throw "Frontend dependencies are missing. Run scripts\setup-local.ps1 first." }

$ApiCommand = "`$Host.UI.RawUI.WindowTitle='Case Management API'; Set-Location '$Api'; & '$Python' -m uvicorn app.main:app --host localhost --port 8000"
$WebCommand = "`$Host.UI.RawUI.WindowTitle='Case Management Web - localhost:3000'; Set-Location '$Web'; & '$Node' '$Vite' --host localhost --port 3000"
$ApiProcess = Start-Process powershell -PassThru -ArgumentList "-NoExit", "-Command", $ApiCommand
$WebProcess = Start-Process powershell -PassThru -ArgumentList "-NoExit", "-Command", $WebCommand
@{api=$ApiProcess.Id;web=$WebProcess.Id} | ConvertTo-Json | Set-Content (Join-Path $Root "data\local-processes.json")

$ApiReady = $false
for ($attempt=0; $attempt -lt 60; $attempt++) {
    try {
        $Health = Invoke-RestMethod "http://localhost:8000/health"
        if ($Health.status -eq "healthy") { $ApiReady = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ApiReady) {
    Write-Error "Case Management API failed to start. Run manually: cd apps\api; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host localhost --port 8000"
    exit 1
}

$WebReady = $false
for ($attempt=0; $attempt -lt 60; $attempt++) {
    try { Invoke-WebRequest "http://localhost:3000/" -UseBasicParsing | Out-Null; $WebReady = $true; break }
    catch { Start-Sleep -Seconds 1 }
}
if (-not $WebReady) {
    Write-Error "Case Management Web failed to start. Run manually: cd apps\web; npm run dev -- --host localhost --port 3000"
    exit 1
}

Start-Process "http://localhost:3000/"
Write-Host "Case Management is healthy at http://localhost:3000/" -ForegroundColor Green
