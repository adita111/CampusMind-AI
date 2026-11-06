
import json
from pathlib import Path
from typing import Optional


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "ulbs_schedule_imported.json"
)


def load_ulbs_activities():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            "ULBS schedule not imported. "
            "Run: python -m services.ulbs_schedule_importer"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        activities = json.load(file)

    if not isinstance(activities, list):
        raise ValueError(
            "ULBS schedule file must contain a list"
        )

    return activities


def get_ulbs_rooms():
    activities = load_ulbs_activities()

    rooms = {
        activity["room_id"]
        for activity in activities
        if activity.get("room_id")
    }

    return sorted(rooms)


def matches_week_parity(activity, week_parity):
    if week_parity == "all":
        return True

    is_odd = activity.get("is_odd_week", False)
    is_even = activity.get("is_even_week", False)

    # Both false is treated as every week.
    if not is_odd and not is_even:
        return True

    if week_parity == "odd":
        return is_odd

    if week_parity == "even":
        return is_even

    return False


def get_ulbs_schedule(
    room_id: Optional[str] = None,
    weekday: Optional[int] = None,
    week_parity: str = "all"
):
    activities = load_ulbs_activities()

    results = []

    for activity in activities:

        if room_id is not None:
            if activity.get("room_id") != room_id:
                continue

        if weekday is not None:
            if activity.get("weekday") != weekday:
                continue

        if not matches_week_parity(
            activity, week_parity
        ):
            continue

        results.append(activity)

    results.sort(
        key=lambda activity: (
            activity.get("weekday", 0),
            activity.get("start_time", ""),
            activity.get("room_id", ""),
            activity.get("id", "")
        )
    )

    return results
