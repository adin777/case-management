$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "apps\api"
$Web = Join-Path $Root "apps\web"
$Python = Join-Path $Api ".venv\Scripts\python.exe"
$Ruff = Join-Path $Api ".venv\Scripts\ruff.exe"
$Mypy = Join-Path $Api ".venv\Scripts\mypy.exe"
$Node = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

if (-not (Test-Path $Python)) { throw "Backend virtual environment is missing: $Python" }
if (-not (Test-Path $Node)) { throw "Bundled Node runtime is missing: $Node" }

$env:RUFF_CACHE_DIR = Join-Path $Root "data\ruff-cache"
$env:MYPY_CACHE_DIR = Join-Path $Root "data\mypy-cache"

Push-Location $Api
try {
    & $Ruff check .
    if ($LASTEXITCODE) { throw "ruff failed" }
    & $Mypy app
    if ($LASTEXITCODE) { throw "mypy failed" }
    & $Python -m pytest app/tests (Join-Path $Root "tests\api_contract")
    if ($LASTEXITCODE) { throw "backend and API contract tests failed" }
}
finally { Pop-Location }

Push-Location $Web
try {
    & $Node node_modules/eslint/bin/eslint.js .
    if ($LASTEXITCODE) { throw "frontend lint failed" }
    & $Node node_modules/typescript/bin/tsc -b --pretty false
    if ($LASTEXITCODE) { throw "frontend typecheck failed" }
    & $Node node_modules/vitest/vitest.mjs run
    if ($LASTEXITCODE) { throw "frontend tests failed" }
    & $Node node_modules/vite/bin/vite.js build
    if ($LASTEXITCODE) { throw "frontend build failed" }
}
finally { Pop-Location }

Write-Host "ALL TESTS PASSED"
