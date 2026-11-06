
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ULBS_FILE = DATA_DIR / "ulbs_schedule_imported.json"
ROOMS_FILE = DATA_DIR / "generated" / "rooms.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_ulbs_activities():
    activities = load_json(ULBS_FILE)

    if not isinstance(activities, list):
        raise ValueError("Invalid ULBS schedule format")

    return activities


def load_rooms():
    rooms = load_json(ROOMS_FILE)

    return {
        room["id"]: room
        for room in rooms
    }


def matches_parity(activity, week_parity):
    if week_parity not in ("odd", "even"):
        raise ValueError(
            "week_parity must be 'odd' or 'even'"
        )

    is_odd = activity.get("is_odd_week", False)
    is_even = activity.get("is_even_week", False)

    if not is_odd and not is_even:
        return True

    if week_parity == "odd":
        return is_odd

    return is_even


def to_minutes(time_string):
    hour, minute = map(int, time_string.split(":"))
    return hour * 60 + minute


def get_simulation_schedule(
    weekday,
    week_parity="odd"
):
    """
    Return ULBS activities for the selected day/week.

    Only rooms that exist in rooms.json are included.
    Student counts remain unknown (None).
    """

    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be between 0 and 6")

    activities = load_ulbs_activities()
    rooms = load_rooms()

    result = []
    seen = set()

    for activity in activities:

        if activity.get("weekday") != weekday:
            continue

        if not matches_parity(activity, week_parity):
            continue

        room_id = activity.get("room_id")

        if room_id not in rooms:
            continue

        start = activity.get("start_time")
        end = activity.get("end_time")

        if not start or not end:
            continue

        start_minute = to_minutes(start)
        end_minute = to_minutes(end)

        if start_minute >= end_minute:
            continue

        activity_id = activity.get("id")

        # Remove duplicate imports of the same ULBS event.
        key = (
            activity_id,
            room_id,
            weekday,
            start,
            end
        )

        if key in seen:
            continue

        seen.add(key)

        result.append({
            "id": str(activity_id),
            "room_id": room_id,
            "course_name": activity.get(
                "course_name", ""
            ),
            "weekday": weekday,
            "start_time": start,
            "end_time": end,
            "group": activity.get("group", ""),
            "students_count": None,
            "activity_type": activity.get(
                "activity_type", "course"
            ),
            "required_equipment": activity.get(
                "required_equipment", []
            ),
            "professor": activity.get("professor"),
            "is_odd_week": activity.get(
                "is_odd_week", False
            ),
            "is_even_week": activity.get(
                "is_even_week", False
            )
        })

    result.sort(
        key=lambda item: (
            item["start_time"],
            item["room_id"]
        )
    )

    return result


def is_room_occupied(
    room_id,
    weekday,
    time,
    week_parity="odd"
):
    current_minute = to_minutes(time)

    activities = get_simulation_schedule(
        weekday,
        week_parity
    )

    for activity in activities:
        if activity["room_id"] != room_id:
            continue

        start = to_minutes(activity["start_time"])
        end = to_minutes(activity["end_time"])

        if start <= current_minute < end:
            return True

    return False
