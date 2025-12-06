# Study Planner — Quick start (Windows)

This repository contains a small Tkinter-based Study Planner GUI. These steps make it easy to get started on Windows (PowerShell/CMD).

## Recommended: use the included venv

1. Create a virtual environment (if you don't have one yet):

```powershell
cd C:\workspace\study_planner
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app using the package entrypoint (works reliably):

```powershell
python -m study_planner
```

or run the helper script while inside the package directory:

```powershell
.\run.ps1
```

3. To run tests:

```powershell
& .venv\Scripts\python.exe -m pytest study_planner/tests
```

## Running inside Visual Studio Code

You can run or debug the app directly in VS Code using the supplied launch configurations.

- If you opened the repository root (C:\workspace) as your workspace:
	- Open the Run view (Ctrl+Shift+D), then select "Run (module) — repo root workspace" and press the green run button.

- If you opened the `study_planner` folder as your workspace:
	- Use "Run (module) — package workspace (cwd = parent)" which runs the module from the parent folder so imports work as expected.
	- You can also run `app.py` directly with the "Run app.py — package workspace" entry.

Notes:
- Make sure VS Code's Python interpreter is set to the project's virtual environment (use Command Palette → Python: Select Interpreter → choose `.venv`).
- The launch configurations also include a "Run tests (pytest) — package tests" profile to run the tests inside VS Code.


## Alternatives

- You can run `python app.py` from inside the `study_planner` folder. The app contains fallback import logic so `app.py` will run as a standalone script, but the package entrypoint is recommended.
- If you're on macOS or Linux, similar commands work with the POSIX venv activation instead.

If you'd like, I can add a small CI workflow (GitHub Actions) to run tests automatically on push.
