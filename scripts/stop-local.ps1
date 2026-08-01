$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "data\local-processes.json"
if (-not (Test-Path $PidFile)) { Write-Host "No recorded local processes were found."; exit 0 }
$Processes = Get-Content $PidFile -Raw | ConvertFrom-Json
foreach ($Id in @($Processes.api, $Processes.web)) {
    $Process = Get-Process -Id $Id -ErrorAction SilentlyContinue
    if ($Process) { Stop-Process -Id $Id }
}
Write-Host "Local Case Management services stopped." -ForegroundColor Green
