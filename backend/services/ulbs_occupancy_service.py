
import json
from datetime import datetime
from pathlib import Path

from services.ulbs_schedule_service import get_ulbs_schedule


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ROOMS_FILE = DATA_DIR / "generated" / "rooms.json"


def load_campus_rooms():
    with ROOMS_FILE.open("r", encoding="utf-8") as file:
        rooms = json.load(file)

    if not isinstance(rooms, list):
        raise ValueError("rooms.json must contain a list")

    return rooms


def get_room_coverage():
    campus_rooms = load_campus_rooms()
    activities = get_ulbs_schedule()

    campus_room_ids = {
        room["id"] for room in campus_rooms
    }

    ulbs_room_ids = {
        activity["room_id"]
        for activity in activities
        if activity.get("room_id")
    }

    matched = sorted(
        campus_room_ids & ulbs_room_ids
    )

    missing = sorted(
        ulbs_room_ids - campus_room_ids
    )

    return {
        "campus_rooms": len(campus_room_ids),
        "ulbs_rooms": len(ulbs_room_ids),
        "matched_rooms": matched,
        "matched_count": len(matched),
        "missing_rooms": missing,
        "missing_count": len(missing),
        "coverage_percentage": round(
            100 * len(matched) / len(ulbs_room_ids),
            2
        ) if ulbs_room_ids else 0.0,
    }


def time_to_minutes(value):
    return (
        datetime.strptime(value, "%H:%M").hour * 60
        + datetime.strptime(value, "%H:%M").minute
    )


def is_activity_active(
    activity,
    weekday,
    time,
    week_parity,
):
    if activity["weekday"] != weekday:
        return False

    if week_parity == "odd":
        if (
            activity.get("is_even_week")
            and not activity.get("is_odd_week")
        ):
            return False

    if week_parity == "even":
        if (
            activity.get("is_odd_week")
            and not activity.get("is_even_week")
        ):
            return False

    current_minutes = time_to_minutes(time)
    start_minutes = time_to_minutes(
        activity["start_time"]
    )
    end_minutes = time_to_minutes(
        activity["end_time"]
    )

    return start_minutes <= current_minutes < end_minutes


def get_room_occupancy(
    weekday,
    time,
    week_parity="odd",
    only_known_rooms=False,
):
    activities = get_ulbs_schedule(
        weekday=weekday,
        week_parity=week_parity,
    )

    campus_rooms = load_campus_rooms()

    campus_room_ids = {
        room["id"] for room in campus_rooms
    }

    occupied_rooms = {}

    for activity in activities:
        room_id = activity["room_id"]

        if only_known_rooms and room_id not in campus_room_ids:
            continue

        if not is_activity_active(
            activity,
            weekday,
            time,
            week_parity,
        ):
            continue

        if room_id not in occupied_rooms:
            occupied_rooms[room_id] = []

        occupied_rooms[room_id].append({
            "id": activity["id"],
            "subject": activity["course_name"],
            "group": activity["group"],
            "start_time": activity["start_time"],
            "end_time": activity["end_time"],
        })

    return {
        "weekday": weekday,
        "time": time,
        "week_parity": week_parity,
        "occupied_rooms_count": len(occupied_rooms),
        "occupied_rooms": occupied_rooms,
    }
