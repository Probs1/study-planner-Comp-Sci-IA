"""Module entrypoint for running the Study Planner as a package.

Run with:
    python -m study_planner

This will start the Tk GUI.
"""

from .app import StudyPlannerApp
import tkinter as tk


def main():
    root = tk.Tk()
    app = StudyPlannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
