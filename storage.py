from pathlib import Path
import json
import uuid
from typing import List, Dict


def default_path() -> Path:
    """Return path to sessions.json in user's home directory for portable execution."""
    app_data_dir = Path.home() / ".study_planner"
    return app_data_dir / "sessions.json"


def save_sessions(sessions: List[Dict], path: Path | str | None = None) -> None:
    if path is None:
        path = default_path()
    else:
        path = Path(path)

    if not isinstance(sessions, list):
        raise ValueError("Sessions must be a list.")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with open(temp_path, "w", encoding="utf-8") as fh:
        json.dump(sessions, fh, indent=2)

    temp_path.replace(path)


def load_sessions(path: Path | str | None = None) -> List[Dict]:
    if path is None:
        path = default_path()
    else:
        path = Path(path)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid sessions file format: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("Sessions file must contain a list of sessions.")

    normalized_sessions = []
    for session in data:
        if not isinstance(session, dict):
            continue
        if "id" not in session or not session.get("id"):
            session["id"] = str(uuid.uuid4())
        normalized_sessions.append(session)

    return normalized_sessions
