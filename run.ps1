<# Start Study Planner (PowerShell)

This script attempts to run the app using the repository's virtual environment (if present),
otherwise falls back to whatever `python` is on PATH.

Usage: .\run.ps1
#>

$packageDir = $PSScriptRoot
# Run from repository root (parent of the package dir) so 'python -m study_planner' finds the package
$projectRoot = Resolve-Path -Path (Join-Path -Path $packageDir -ChildPath '..')
Push-Location -Path $projectRoot
try {
    $venvExe = Join-Path -Path $packageDir -ChildPath ".venv\Scripts\python.exe"
    if (Test-Path $venvExe) {
        & $venvExe -m study_planner
    } else {
        Write-Host "No .venv found — using 'python' from PATH."
        python -m study_planner
    }
} finally {
    Pop-Location
}
