"""JSON-based storage for study sessions."""
from pathlib import Path
import json
import uuid
from typing import List, Dict


def default_path() -> Path:
    return Path(__file__).parent / "sessions.json"


def save_sessions(sessions: List[Dict], path: Path | str | None = None) -> None:
    if path is None:
        path = default_path()
    else:
        path = Path(path)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sessions, fh, indent=2)


def load_sessions(path: Path | str | None = None) -> List[Dict]:
    if path is None:
        path = default_path()
    else:
        path = Path(path)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                for s in data:
                    if "id" not in s:
                        s["id"] = str(uuid.uuid4())
                return data
            return []
    except FileNotFoundError:
        return []
