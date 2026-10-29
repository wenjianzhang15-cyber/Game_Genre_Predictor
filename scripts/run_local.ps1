$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Create the project virtual environment first; see README.md.'
}
$env:OMP_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
Push-Location $projectRoot
try {
    & $projectPython -m uvicorn app:app --host 127.0.0.1 --port 7860
} finally {
    Pop-Location
}
