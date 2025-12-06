from study_planner.storage import save_sessions, load_sessions


def test_save_and_load(tmp_path):
    f = tmp_path / "sessions.json"
    sessions = [
        {"subject": "Math", "day": "Monday", "start": "09:00", "end": "10:00", "color": "#fff"}
    ]

    # Save sessions
    save_sessions(sessions, path=str(f))

    # Load sessions and ensure data preserved and id set
    loaded = load_sessions(path=str(f))
    assert isinstance(loaded, list)
    assert len(loaded) == 1
    s = loaded[0]
    assert s["subject"] == "Math"
    assert "id" in s
