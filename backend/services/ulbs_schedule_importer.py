
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://schedule.ulbsibiu.ro"
FACULTY = "ing"
PLANNING_TIME_UNIT_ID = 6

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

STRUCTURE_FILE = DATA_DIR / "ulbs_structure.json"
RAW_FILE = DATA_DIR / "ulbs_schedule_raw.json"
IMPORTED_FILE = DATA_DIR / "ulbs_schedule_imported.json"

REQUEST_DELAY_SECONDS = 0.5

WEEKDAYS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

ACTIVITY_TYPES = {
    "Curs": "course",
    "Seminar": "seminar",
    "Laborator": "laboratory",
    "Proiect": "project",
}


def fetch_json(path, params=None):
    query = urlencode(params or {})
    url = f"{BASE_URL}{path}"

    if query:
        url += f"?{query}"

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "CampusMind-AI/1.0",
        },
    )

    try:
        with urlopen(request, timeout=25) as response:
            payload = json.load(response)

    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Could not retrieve ULBS data from {url}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Unexpected ULBS API response")

    if payload.get("success") is not True:
        raise ValueError(
            payload.get("message", "ULBS API request failed")
        )

    if not isinstance(payload.get("data"), list):
        raise ValueError("ULBS API returned invalid data")

    return payload


def fetch_faculty_structure():
    return fetch_json(
        f"/api/faculties/{FACULTY}/structure",
        {
            "planning_time_unit_id": PLANNING_TIME_UNIT_ID
        },
    )


def fetch_formation_schedule(formation_id):
    return fetch_json(
        f"/api/faculties/{FACULTY}"
        f"/study-formations/{formation_id}/schedule",
        {
            "planning_time_unit_id": PLANNING_TIME_UNIT_ID
        },
    )


def collect_formations(structure_payload):
    formations = {}
    root_ids = []

    def visit(node, department_name, parent_id=None):
        formation = node.get("studyFormation")

        if not isinstance(formation, dict):
            return

        formation_id = formation.get("id")

        if formation_id is None:
            return

        formations[formation_id] = {
            "id": formation_id,
            "name": formation.get("name", ""),
            "level": formation.get("level"),
            "parent_id": parent_id,
            "department_name": department_name,
        }

        if parent_id is None:
            root_ids.append(formation_id)

        for child in node.get("children", []):
            visit(child, department_name, formation_id)

    for department_entry in structure_payload["data"]:
        department = department_entry.get("department") or {}
        department_name = department.get("name", "")

        for root in department_entry.get("children", []):
            visit(root, department_name)

    return formations, sorted(set(root_ids))


def normalize_schedules(responses, formations):
    unique_activities = {}

    for requested_formation_id, payload in responses.items():

        for entry in payload["data"]:
            entry_formation = entry.get("studyFormation") or {}

            for schedule in entry.get("schedules", []):
                schedule_id = schedule.get("id")
                room = schedule.get("room")
                subject = schedule.get("subject")
                weekday = WEEKDAYS.get(schedule.get("day"))

                if (
                    schedule_id is None
                    or not room
                    or not subject
                    or weekday is None
                ):
                    continue

                schedule_formation = (
                    schedule.get("studyFormation")
                    or entry_formation
                )

                formation_id = schedule_formation.get("id")
                formation_name = schedule_formation.get(
                    "name", ""
                )

                activity_type_data = (
                    schedule.get("activityType") or {}
                )

                activity_type_name = activity_type_data.get(
                    "name", ""
                )

                activity_type = ACTIVITY_TYPES.get(
                    activity_type_name,
                    activity_type_name.lower(),
                )

                for slot in schedule.get("timeSlots", []):
                    slot_id = slot.get("id")
                    start_time = slot.get("startTime")
                    end_time = slot.get("endTime")

                    if (
                        slot_id is None
                        or not start_time
                        or not end_time
                    ):
                        continue

                    # The same schedule and time slot can appear
                    # in multiple responses from the hierarchy.
                    key = (schedule_id, slot_id)

                    if key not in unique_activities:
                        unique_activities[key] = {
                            "id": f"ULBS_{schedule_id}_{slot_id}",
                            "room_id": room,
                            "course_name": subject,
                            "weekday": weekday,
                            "start_time": start_time,
                            "end_time": end_time,
                            "group": formation_name,
                            "students_count": None,
                            "activity_type": activity_type,
                            "required_equipment": [],
                            "professor": schedule.get("professor"),
                            "is_odd_week": schedule.get(
                                "isOddWeek", False
                            ),
                            "is_even_week": schedule.get(
                                "isEvenWeek", False
                            ),
                            "source": "ULBS",
                            "source_schedule_id": schedule_id,
                            "source_slot_id": slot_id,
                            "source_room_id": schedule.get("roomId"),
                            "formation_ids": [],
                            "formation_names": [],
                            "requested_formation_ids": [],
                        }

                    activity = unique_activities[key]

                    if (
                        formation_id is not None
                        and formation_id not in activity["formation_ids"]
                    ):
                        activity["formation_ids"].append(formation_id)

                    if (
                        formation_name
                        and formation_name not in activity["formation_names"]
                    ):
                        activity["formation_names"].append(
                            formation_name
                        )

                    if (
                        requested_formation_id
                        not in activity["requested_formation_ids"]
                    ):
                        activity["requested_formation_ids"].append(
                            requested_formation_id
                        )

    activities = list(unique_activities.values())

    activities.sort(
        key=lambda activity: (
            activity["weekday"],
            activity["start_time"],
            activity["room_id"],
            activity["id"],
        )
    )

    return activities


def create_room_schedule(activities):
    rooms = defaultdict(list)

    for activity in activities:
        rooms[activity["room_id"]].append(activity)

    return dict(sorted(rooms.items()))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def import_ulbs_schedule():
    print("Fetching ULBS faculty structure...")

    structure = fetch_faculty_structure()
    formations, root_ids = collect_formations(structure)

    if not root_ids:
        raise ValueError("No top-level study formations found")

    print(f"Discovered {len(formations)} formations")
    print(f"Top-level formations: {len(root_ids)}")

    responses = {}
    errors = []

    for index, formation_id in enumerate(root_ids, start=1):
        name = formations[formation_id]["name"]

        print(
            f"[{index}/{len(root_ids)}] "
            f"Fetching {name} ({formation_id})..."
        )

        try:
            responses[formation_id] = (
                fetch_formation_schedule(formation_id)
            )

        except (RuntimeError, ValueError) as exc:
            errors.append({
                "formation_id": formation_id,
                "error": str(exc),
            })
            print(f"  Error: {exc}")

        if index < len(root_ids):
            time.sleep(REQUEST_DELAY_SECONDS)

    activities = normalize_schedules(
        responses,
        formations,
    )

    room_schedules = create_room_schedule(activities)

    imported_at = datetime.now(
        timezone.utc
    ).isoformat()

    save_json(STRUCTURE_FILE, structure)

    save_json(RAW_FILE, {
        "imported_at": imported_at,
        "requested_root_ids": root_ids,
        "responses": responses,
        "errors": errors,
    })

    save_json(IMPORTED_FILE, activities)

    summary = {
        "status": (
            "success"
            if not errors
            else "partial"
        ),
        "faculty": FACULTY,
        "planning_time_unit_id": PLANNING_TIME_UNIT_ID,
        "formations_discovered": len(formations),
        "root_formations": len(root_ids),
        "successful_requests": len(responses),
        "failed_requests": len(errors),
        "activities_imported": len(activities),
        "rooms_found": len(room_schedules),
        "room_ids": list(room_schedules.keys()),
        "errors": errors,
        "completeness_verified": False,
    }

    print(json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ))

    return summary


if __name__ == "__main__":
    import_ulbs_schedule()
