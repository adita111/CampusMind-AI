
from collections import defaultdict
from datetime import time

from ortools.sat.python import cp_model

from services.room_service import get_all_rooms
from services.schedule_service import get_all_activities


def to_minutes(value: str) -> int:
    parsed = time.fromisoformat(value)
    return parsed.hour * 60 + parsed.minute


def overlaps(a, b) -> bool:
    if a.weekday != b.weekday:
        return False

    return (
        to_minutes(a.start_time) < to_minutes(b.end_time)
        and to_minutes(b.start_time) < to_minutes(a.end_time)
    )


def optimize_schedule():
    rooms = [
        room for room in get_all_rooms()
        if room.room_type != "hallway"
    ]

    activities = get_all_activities()

    if not activities:
        return {
            "status": "success",
            "original_zone_count": 0,
            "optimized_zone_count": 0,
            "moved_activities": 0,
            "activities": []
        }

    model = cp_model.CpModel()

    assignments = {}
    compatible_rooms = {}

    # 1. Find suitable rooms for each activity
    for activity in activities:
        compatible = [
            room for room in rooms
            if room.capacity >= activity.students_count
            and all(
                equipment in room.equipment
                for equipment in activity.required_equipment
            )
            and (
                activity.activity_type != "laboratory"
                or room.room_type in ("laboratory", "lab")
            )
        ]

        if not compatible:
            raise ValueError(
                f"No compatible room for {activity.id}"
            )

        compatible_rooms[activity.id] = compatible

        variables = []

        for room in compatible:
            variable = model.NewBoolVar(
                f"{activity.id}_{room.id}"
            )

            assignments[(activity.id, room.id)] = variable
            variables.append(variable)

        # Each activity must use exactly one room
        model.Add(sum(variables) == 1)

    # 2. Prevent overlapping activities in one room
    for i, first in enumerate(activities):
        for second in activities[i + 1:]:
            if not overlaps(first, second):
                continue

            for room in rooms:
                first_key = (first.id, room.id)
                second_key = (second.id, room.id)

                if (
                    first_key in assignments
                    and second_key in assignments
                ):
                    model.Add(
                        assignments[first_key]
                        + assignments[second_key] <= 1
                    )

    # 3. Minimize the number of heating zones used
    zone_variables = {}

    for zone_id in {room.heating_zone for room in rooms}:
        zone_used = model.NewBoolVar(
            f"zone_{zone_id}"
        )

        zone_variables[zone_id] = zone_used

        for activity in activities:
            for room in compatible_rooms[activity.id]:
                if room.heating_zone == zone_id:
                    model.Add(
                        assignments[(activity.id, room.id)]
                        <= zone_used
                    )

    # 4. Penalize unnecessary room changes
    moved_variables = []

    for activity in activities:
        for room in compatible_rooms[activity.id]:
            if room.id != activity.room_id:
                moved_variables.append(
                    assignments[(activity.id, room.id)]
                )

    # Prioritize fewer zones, then fewer moves
    zone_weight = len(activities) + 1

    model.Minimize(
        zone_weight * sum(zone_variables.values())
        + sum(moved_variables)
    )

    # 5. Solve optimization problem
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):
        raise ValueError(
            "No valid schedule could be generated"
        )

    # 6. Build optimized result
    result = []
    optimized_zones = set()
    moved_count = 0

    room_by_id = {room.id: room for room in rooms}

    original_zones = {
        room_by_id[activity.room_id].heating_zone
        for activity in activities
        if activity.room_id in room_by_id
    }

    for activity in activities:
        for room in compatible_rooms[activity.id]:
            variable = assignments[(activity.id, room.id)]

            if solver.Value(variable) == 1:
                optimized_zones.add(room.heating_zone)

                moved = room.id != activity.room_id

                if moved:
                    moved_count += 1

                result.append({
                    **activity.model_dump(),
                    "original_room_id": activity.room_id,
                    "room_id": room.id,
                    "heating_zone": room.heating_zone,
                    "moved": moved
                })

                break

    return {
        "status": "success",
        "original_zone_count": len(original_zones),
        "optimized_zone_count": len(optimized_zones),
        "moved_activities": moved_count,
        "activities": result
    }
