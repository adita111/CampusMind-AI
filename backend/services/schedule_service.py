
import json
from pathlib import Path

from models.scheduled_activity import ScheduledActivity


SCHEDULE_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "schedule.json"
)


def get_all_activities() -> list[ScheduledActivity]:
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [ScheduledActivity(**item) for item in data]


def get_room_schedule(room_id: str) -> list[ScheduledActivity]:
    activities = get_all_activities()

    return [
        activity
        for activity in activities
        if activity.room_id == room_id
    ]
