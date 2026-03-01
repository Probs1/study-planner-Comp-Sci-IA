# 📚 Weekly Study Planner

A comprehensive desktop app for organizing and tracking your study sessions. Built with Python and Tkinter.

## Features

- **Session Management**: Create, edit, and delete study sessions with custom colors
- **Recurring Events**: Schedule sessions across multiple days at once
- **Task Lists**: Add and track tasks for each study session
- **Statistics Dashboard**: Visualize your study time and progress towards goals
- **Smart Reminders**: Get notified 60min, 30min, and at session start
- **Time Conflict Detection**: Avoid double-booking your study time
- **Filter & Search**: Filter calendar by subject
- **Multi-Week View**: Plan ahead with week navigation
- **Dark Mode**: Easy on the eyes for night studying
- **Export/Import**: Backup and share your schedules as JSON

## Quick Start

### Requirements

- Python 3.10+
- No external dependencies (uses built-in tkinter)

### Running the App

```python
python app.py
```

Or if you have the package structure:

```python
python run_app.py
```

### First Time Setup

1. Clone the repository
2. Navigate to the project directory
3. Run the app - that's it!

Your sessions are automatically saved to `sessions.json`.

## How to Use

### Adding a Session

1. Click "➕ Add Session" or press `Ctrl+N`
2. Fill in subject, day, times, and optional notes
3. Choose a color to color-code your subjects
4. For recurring sessions, check the box and select multiple days

### Editing Sessions

- **Double-click** any session to edit it
- **Right-click** to open context menu with more options

### Managing Tasks

1. Right-click a session
2. Select "📝 Manage Tasks"
3. Add tasks and check them off as you complete them

### Viewing Statistics

- Click "📊 Statistics" button to see:
  - Total study hours
  - Time breakdown by subject
  - Progress towards your weekly goal

### Keyboard Shortcuts

- `Ctrl+N` - Add new session
- `Ctrl+E` - Export schedule
- `Ctrl+S` - Show statistics  
- `Ctrl+F` - Filter by subject
- `Ctrl+D` - Toggle dark mode
- `Ctrl+←/→` - Navigate weeks

## File Structure

```
study-planner-Comp-Sci-IA/
├── app.py              # Main application
├── storage.py          # Session storage (JSON)
├── time_utils.py       # Time formatting utilities
├── run_app.py          # Alternative launcher
├── sessions.json       # Your saved sessions
└── FEATURE_SHOWCASE.md # Complete feature documentation
```

## Tips

- **Color-code your subjects** (e.g., Blue for Math, Red for English)
- **Use notes field** for homework details or chapter numbers
- **Set realistic goals** in the Study Goals menu
- **Export regularly** to backup your schedule

## Development

### Running Tests

```python
python -m pytest tests/
```

### Project Background

This was built as a Computer Science IA project to help students organize their study time more effectively. Started with basic scheduling and grew to include all the features I wished commercial planners had.

## License

Free to use and modify for personal and educational purposes.

---

Made with ☕ and lots of late-night coding sessions


- You can run `python app.py` from inside the `study_planner` folder. The app contains fallback import logic so `app.py` will run as a standalone script, but the package entrypoint is recommended.
- If you're on macOS or Linux, similar commands work with the POSIX venv activation instead.

If you'd like, I can add a small CI workflow (GitHub Actions) to run tests automatically on push.
