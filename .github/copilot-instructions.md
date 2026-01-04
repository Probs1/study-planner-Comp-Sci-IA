# Study Planner — AI Coding Agent Instructions

## Project Overview
This is a **Tkinter-based GUI Study Planner** for Computer Science IA. The app displays a 7-day weekly calendar grid where users can add, view, and delete study sessions across time slots (default: 15:30-22:00 in 30-minute intervals).

**Key components:**
- `app.py`: Main `StudyPlannerApp` class with Tkinter GUI logic
- `storage.py`: JSON persistence layer (`sessions.json`)
- `time_utils.py`: Time formatting and slot generation utilities
- `__main__.py`: Package entrypoint for `python -m study_planner`
- `run_app.py`: Fallback script with path manipulation for direct execution

## Architecture & Design Patterns

### Dual Import Strategy
The codebase supports **both package mode and standalone script execution**:
```python
try:
    from . import storage  # Package import
    from .time_utils import format_min
except Exception: 
    import storage  # Fallback for standalone
    from time_utils import format_min
```
**When to maintain this pattern:** Always preserve this try/except structure in modules that might run standalone (like `app.py`).

### Session Data Model
Sessions are stored as dictionaries with **required fields:**
```python
{
    "id": str(uuid.uuid4()),      # Auto-generated UUID
    "subject": "Math",
    "day": "Monday",              # Must match self.days list
    "start": "09:00",             # HH:MM format
    "end": "10:30",               # HH:MM format
    "color": "#AED6F1"            # Hex color
}
```

### Time Representation
- **Internal:** Minutes since midnight (int) — e.g., `930` for 15:30
- **Display/Storage:** HH:MM string format — e.g., `"15:30"`
- **Conversion:** Use `format_min(minutes)` to convert int → string

### Block-Based Calendar Rendering
Sessions render into **time slot blocks** (not absolute positioning). A 2-hour session spanning 4 slots will create 4 separate visual blocks. The rendering logic in `render_sessions()` checks overlap:
```python
if start_minutes < slot_end and end_minutes > slot_start:
    # Render session in this slot
```

## Critical Developer Workflows

### Running the Application
**Preferred method (package mode):**
```powershell
python -m study_planner
```

**Alternative helper scripts:**
```powershell
.\run.ps1          # PowerShell (auto-detects .venv)
.\start.bat        # CMD batch file
python run_app.py  # Direct script execution
```

**Important:** Always run from the **repository root** (parent of package dir) so module imports resolve correctly.

### Running Tests
```powershell
# With venv activated:
python -m pytest tests/

# Or using absolute venv path:
& .venv\Scripts\python.exe -m pytest tests/
```

Tests use `tmp_path` fixture for isolated file operations. See `test_storage.py` for pattern.

### Setting Up Environment
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Note:** Only dependency is `pytest` — the app uses stdlib only (tkinter, json, uuid, pathlib).

## Project-Specific Conventions

### Error Handling Philosophy
- **Storage layer** (`storage.py`): Raises exceptions, never shows message boxes
- **GUI layer** (`app.py`): Catches exceptions and displays `messagebox.showerror()`
- **Graceful degradation:** If `sessions.json` doesn't exist, `load_sessions()` returns `[]`

### Widget Management in Calendar Grid
The calendar uses **persistent grid cells** (`self.slot_frames`) that are never destroyed. When re-rendering:
1. Iterate through all `slot_frames[row][col]`
2. Delete child widgets EXCEPT those marked with `is_time_label = True`
3. Create new session blocks as needed

**Example from `render_sessions()`:**
```python
for child in cell.winfo_children():
    if getattr(child, "is_time_label", False):
        continue  # Preserve time label
    child.destroy()
```

### Session Deletion Behavior
Users can delete sessions two ways:
1. **Remove single block** — Splits session into left/right remainders (see `_remove_block_from_session`)
2. **Remove entire session** — Deletes all blocks across all slots

**Edge case:** If a session fits entirely within a block, "Remove this block" behaves like "Remove entire session".

### UUID Generation
Always use `str(uuid.uuid4())` for new session IDs. The `load_sessions()` function auto-generates IDs for legacy data missing them:
```python
for s in data:
    if "id" not in s:
        s["id"] = str(uuid.uuid4())
```

## Integration Points

### Storage Abstraction
`storage.py` provides `default_path()` that resolves to `<package_dir>/sessions.json`. For testing, pass explicit `path` parameter:
```python
save_sessions(sessions, path=tmp_path / "test.json")
```

### Time Slot Configuration
Default slots: **15:30 to 22:00** in **30-minute intervals**. Configured in `_create_calendar_grid()`:
```python
self.time_slots = generate_time_slots(
    start_min=15*60+30,  # 15:30
    end_min=22*60,       # 22:00
    interval_length=30   # 30 minutes
)
```
**To change:** Modify these parameters — calendar grid adjusts automatically.

## Common Pitfalls

1. **Import errors when running from wrong directory:** Always run from repo root, not inside package dir
2. **Modifying time labels during render:** Check `is_time_label` attribute before destroying widgets
3. **Forgetting to save after session changes:** Always call `storage.save_sessions(self.sessions)` after modifications
4. **Hardcoded day names:** Days must exactly match `self.days` list (case-sensitive)
5. **Time parsing failures:** Always wrap time string parsing in try/except and handle gracefully

## Testing Patterns

- Use `tmp_path` fixture for file operations (pytest provides this)
- Import from package namespace: `from study_planner.storage import ...`
- Tests assume module structure, not standalone script usage
- Verify `id` field auto-generation in loaded sessions

## Windows-Specific Notes

This project is **Windows-first** (PowerShell/.bat scripts, path conventions in README). When adding shell commands:
- Use PowerShell syntax by default
- Use `;` for command chaining (NOT `&&`)
- Use `& executable` syntax for paths with spaces
- Virtual environment activation: `. .venv\Scripts\Activate.ps1`
