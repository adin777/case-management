$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Branch = git -C $Root branch --show-current
$Commit = git -C $Root rev-parse HEAD
$Changes = @(git -C $Root status --porcelain)

Write-Host "Branch: $Branch"
Write-Host "Commit: $Commit"
Write-Host "Modified/untracked source files:"
if ($Changes.Count -eq 0) {
    Write-Host "  none"
    exit 0
}
$Changes | ForEach-Object { Write-Host "  $_" }
Write-Error "Source changes are not committed."
exit 1
