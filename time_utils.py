

from typing import List, Tuple


def format_min(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def generate_time_slots(start_min: int = 15*60 + 30, end_min: int = 22*60, interval_length: int = 30) -> List[Tuple[int, int]]:
    slots = []
    current = start_min

    while current + interval_length <= end_min:
        slot_start = current
        slot_end = current + interval_length
        slots.append((slot_start, slot_end))
        current = slot_end

    return slots
