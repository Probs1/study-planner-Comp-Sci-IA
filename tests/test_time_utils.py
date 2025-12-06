from study_planner.time_utils import format_min, generate_time_slots


def test_format_min():
    assert format_min(0) == "00:00"
    assert format_min(9) == "00:09"
    assert format_min(60) == "01:00"
    assert format_min(90) == "01:30"


def test_generate_time_slots_default():
    slots = generate_time_slots()
    # Ensure slots are 30-minute intervals
    assert all(end - start == 30 for start, end in slots)
    assert slots[0][0] == 15 * 60 + 30
    assert slots[-1][1] <= 22 * 60
