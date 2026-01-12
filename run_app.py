"""Convenience script to start the Study Planner when run directly.

Usage:
    python run_app.py

This uses package imports so it works from the project directory.
"""

from __future__ import annotations

try:
    # When used as a package (python -m study_planner.run_app) this works
    from .app import StudyPlannerApp
except Exception:
    # When run directly as a script (python run_app.py) the package context is missing.
    # Make sure the project root (parent of this package dir) is on sys.path and import via package.
    import os
    import sys

    pkg_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(pkg_dir, os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from app import StudyPlannerApp
import tkinter as tk


def main():
    root = tk.Tk()
    app = StudyPlannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
