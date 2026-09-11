param([string[]]$BackendTests = @("app/tests/test_transfer_and_knowledge.py", "app/tests/test_directory_lifecycle.py"))
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "apps/api/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) { throw "API virtual environment is missing: $python" }
Push-Location (Join-Path $repo "apps/api")
try {
    & $python -m ruff check app
    if ($LASTEXITCODE -ne 0) { throw "Ruff failed" }
    & $python -m mypy app
    if ($LASTEXITCODE -ne 0) { throw "Mypy failed" }
    & $python -m pytest @BackendTests -q
    if ($LASTEXITCODE -ne 0) { throw "Focused backend tests failed" }
} finally { Pop-Location }
Push-Location (Join-Path $repo "apps/web")
try {
    $node = Join-Path $env:USERPROFILE ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    if (-not (Test-Path $node)) { throw "Bundled Node runtime is missing: $node" }
    & $node node_modules/eslint/bin/eslint.js .
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed" }
    & $node node_modules/typescript/bin/tsc -b --pretty false
    if ($LASTEXITCODE -ne 0) { throw "Frontend typecheck failed" }
} finally { Pop-Location }
