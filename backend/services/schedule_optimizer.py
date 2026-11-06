from services.room_service import get_all_rooms
from services.schedule_service import get_all_activities


def optimize_schedule(activities=None):
    """Conservative behavior for official ULBS schedules.

    Do not reassign real activities based on fabricated room capacities or
    unknown group sizes/equipment. The safe baseline is the original timetable.
    The original OR-Tools optimizer may be reintroduced once these constraints
    are verified, preferably as a separately enabled proposal mode.
    """
    if activities is None:
        activities = get_all_activities()

    room_by_id = {room.id: room for room in get_all_rooms()}
    original_zones = {
        room_by_id[a.room_id].heating_zone
        for a in activities if a.room_id in room_by_id
    }

    return {
        "status": "skipped_unverified_capacity" if activities else "success",
        "message": (
            "ULBS room capacities and enrollment are unverified. "
            "Original room assignments preserved."
            if activities else "No activities to optimize."
        ),
        "original_zone_count": len(original_zones),
        "optimized_zone_count": len(original_zones),
        "moved_activities": 0,
        "activities": [
            {
                **a.model_dump(),
                "original_room_id": a.room_id,
                "heating_zone": (
                    room_by_id[a.room_id].heating_zone
                    if a.room_id in room_by_id else None
                ),
                "moved": False,
            }
            for a in activities
        ],
    }
