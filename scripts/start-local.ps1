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

New-Item -ItemType Directory -Force (Join-Path $Root "data") | Out-Null
$Repository = git -C $Root remote get-url origin
$Branch = git -C $Root branch --show-current
$Commit = git -C $Root rev-parse --short HEAD
$Dirty = @(git -C $Root status --porcelain).Count -gt 0
Write-Host "Repository: $Repository"
Write-Host "Branch: $Branch"
Write-Host "Commit: $Commit"
Write-Host "Working tree: $(if ($Dirty) { 'dirty' } else { 'clean' })"
if ($Dirty) { Write-Warning "WARNING: קיימים קבצים ששונו מקומית ולא נשמרו ב-Git." }

Push-Location $Api
try {
    & $Python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Alembic migration failed." }
    & $Python -m app.seed
    if ($LASTEXITCODE -ne 0) { throw "Admin bootstrap failed." }
} finally { Pop-Location }

$ApiCommand = "`$Host.UI.RawUI.WindowTitle='Case Management API'; Set-Location '$Api'; & '$Python' -m uvicorn app.main:app --host localhost --port 8000"
$WebCommand = "`$Host.UI.RawUI.WindowTitle='Case Management Web - localhost:3000'; Set-Location '$Web'; & '$Node' '$Vite' --host localhost --port 3000"
$ApiReady = $false
try {
    $Health = Invoke-RestMethod "http://localhost:8000/health"
    $ApiReady = $Health.status -eq "healthy"
} catch { }
if (-not $ApiReady) {
    $ApiProcess = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList "-NoExit", "-Command", $ApiCommand
}
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
try {
    Invoke-WebRequest "http://localhost:3000/" -UseBasicParsing | Out-Null
    $WebReady = $true
} catch { }
if (-not $WebReady) {
    $WebProcess = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList "-NoExit", "-Command", $WebCommand
}
for ($attempt=0; $attempt -lt 60; $attempt++) {
    try { Invoke-WebRequest "http://localhost:3000/" -UseBasicParsing | Out-Null; $WebReady = $true; break }
    catch { Start-Sleep -Seconds 1 }
}

@{
    api = if ($ApiProcess) { $ApiProcess.Id } else { $null }
    web = if ($WebProcess) { $WebProcess.Id } else { $null }
} | ConvertTo-Json | Set-Content (Join-Path $Root "data\local-processes.json")
if (-not $WebReady) {
    Write-Error "Case Management Web failed to start. Run manually: cd apps\web; npm run dev -- --host localhost --port 3000"
    exit 1
}

Write-Host "Case Management is healthy at http://localhost:3000/" -ForegroundColor Green
