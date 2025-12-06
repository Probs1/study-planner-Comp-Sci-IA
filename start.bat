@echo off
REM Start Study Planner using the local virtual environment if present
REM Ensure we run from repository root (parent of this package folder)
PUSHD "%~dp0.."
IF EXIST "%~dp0\.venv\Scripts\python.exe" (
  "%~dp0\.venv\Scripts\python.exe" -m study_planner
) ELSE (
  echo No .venv found - falling back to python on PATH
  python -m study_planner
)
POPD
