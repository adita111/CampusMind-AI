import json
from datetime import time
from pathlib import Path

from models.scheduled_activity import ScheduledActivity

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "ulbs_schedule_imported.json"


def _to_minutes(value: str) -> int:
    parsed = time.fromisoformat(value)
    return parsed.hour * 60 + parsed.minute


def _matches_week(activity: ScheduledActivity, parity: str) -> bool:
    if parity == "all":
        return True
    if parity not in {"odd", "even"}:
        raise ValueError("week_parity must be 'odd', 'even' or 'all'")
    # The ULBS response can mark neither flag for a weekly activity.
    # Verify this convention against the official timetable before a production deployment.
    is_odd_week = getattr(activity, "is_odd_week", False)
    is_even_week = getattr(activity, "is_even_week", False)
    if not is_odd_week and not is_even_week:
        return True
    return is_odd_week if parity == "odd" else is_even_week


def get_all_activities(
    weekday: int | None = None,
    week_parity: str = "all",
) -> list[ScheduledActivity]:
    if weekday is not None and not 0 <= weekday <= 6:
        raise ValueError("weekday must be between 0 and 6")
    if week_parity not in {"all", "odd", "even"}:
        raise ValueError("week_parity must be 'all', 'odd' or 'even'")
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            "Missing ulbs_schedule_imported.json; run: "
            "python -m services.ulbs_schedule_importer"
        )
    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    if not isinstance(raw, list):
        raise ValueError("ULBS schedule must be a JSON list")

    activities = []
    seen = set()
    for item in raw:
        activity = ScheduledActivity.model_validate(item)
        if weekday is not None and activity.weekday != weekday:
            continue
        if not _matches_week(activity, week_parity):
            continue
        if _to_minutes(activity.start_time) >= _to_minutes(activity.end_time):
            continue
        identity = (activity.id, activity.room_id, activity.weekday,
                    activity.start_time, activity.end_time)
        if identity in seen:
            continue
        seen.add(identity)
        activities.append(activity)
    activities.sort(key=lambda a: (a.weekday, a.start_time, a.room_id, a.id))
    return activities


def get_room_schedule(
    room_id: str, weekday: int | None = None, week_parity: str = "all"
) -> list[ScheduledActivity]:
    return [activity for activity in get_all_activities(weekday, week_parity)
            if activity.room_id == room_id]
