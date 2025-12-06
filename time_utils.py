"""Time-related utilities used by the Study Planner app."""

from typing import List, Tuple


def format_min(total_minutes: int) -> str:
    """Converts minutes since midnight into 'HH:MM' format."""
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def generate_time_slots(start_min: int = 15*60 + 30, end_min: int = 22*60, interval_length: int = 30) -> List[Tuple[int, int]]:
    """Generate 30-minute time interval slots between start and end minutes.

    Returns a list of (start_min, end_min) tuples.
    """
    slots = []
    current = start_min

    while current + interval_length <= end_min:
        slot_start = current
        slot_end = current + interval_length
        slots.append((slot_start, slot_end))
        current = slot_end

    return slots
