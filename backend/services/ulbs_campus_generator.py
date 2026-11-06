
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCE_FILE = DATA_DIR / "ulbs_schedule_imported.json"
GENERATED_DIR = DATA_DIR / "generated"

OUTPUT_FILES = [
    "buildings.json",
    "floors.json",
    "rooms.json",
    "room_states.json",
    "heating_zones.json",
    "sensors.json",
]

# All values below are DEMO assumptions, not ULBS measurements.
ROOMS_PER_ZONE = 5
DEFAULT_EQUIPMENT = ["projector"]


def stable_number(value, minimum, maximum):
    digest = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()

    number = int(digest[:12], 16)
    return minimum + number % (maximum - minimum + 1)


def load_ulbs_activities():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            "Missing ulbs_schedule_imported.json. "
            "Run the ULBS importer first."
        )

    with SOURCE_FILE.open("r", encoding="utf-8") as file:
        activities = json.load(file)

    if not isinstance(activities, list):
        raise ValueError("ULBS data must be a JSON list")

    return activities


def parse_room_location(room_id):
    # Example: IE305 -> building IE, floor 3
    match = re.match(
        r"^([A-Za-z]+)(\d+)",
        room_id.strip()
    )

    if match:
        building_id = match.group(1).upper()
        digits = match.group(2)

        if len(digits) >= 3:
            floor = int(digits[0])
        else:
            floor = 0

        return building_id, floor

    # Unknown room naming convention
    return "UNKNOWN", 0


def get_room_type(activities):
    types = {
        str(activity.get("activity_type", "")).lower()
        for activity in activities
    }

    # This is only a demo assumption.
    if "laboratory" in types:
        return "laboratory"

    return "classroom"


def generate_campus(activities):
    activities_by_room = {}

    for activity in activities:
        room_id = str(
            activity.get("room_id") or ""
        ).strip()

        if not room_id:
            continue

        activities_by_room.setdefault(
            room_id, []
        ).append(activity)

    if not activities_by_room:
        raise ValueError(
            "No rooms found in imported ULBS activities"
        )

    buildings_map = {}
    floors_map = {}
    rooms = []
    room_states = []
    sensors = []
    rooms_by_floor = {}

    for room_id in sorted(activities_by_room):
        building_id, floor_number = parse_room_location(
            room_id
        )

        floor_id = f"{building_id}_F{floor_number}"

        buildings_map[building_id] = {
            "id": building_id,
            "name": (
                f"Building {building_id}"
                if building_id != "UNKNOWN"
                else "Unclassified rooms"
            ),
        }

        floors_map[floor_id] = {
            "id": floor_id,
            "building_id": building_id,
            "number": floor_number,
            "name": f"Floor {floor_number}",
        }

        area = stable_number(
            f"{room_id}:area", 40, 110
        )

        capacity = stable_number(
            f"{room_id}:capacity", 40, 100
        )

        initial_temp = (
            stable_number(
                f"{room_id}:temperature", 180, 220
            ) / 10
        )

        # Approximate parameters for a thermal demo.
        heat_loss = round(area * 1.35, 2)
        thermal_capacity = float(area * 220000)
        heating_power = float(area * 65)

        room = {
            "id": room_id,
            "building": building_id,
            "floor": floor_number,
            "area_m2": float(area),
            "capacity": capacity,
            "room_type": get_room_type(
                activities_by_room[room_id]
            ),
            "equipment": DEFAULT_EQUIPMENT.copy(),
            "heating_zone": "",
            "heat_loss_coefficient": heat_loss,
            "thermal_capacity": thermal_capacity,
            "heating_power": heating_power,
        }

        rooms.append(room)

        room_states.append({
            "room_id": room_id,
            "current_temperature": initial_temp,
            "target_temperature": 21.0,
            "heating_on": False,
            "lights_on": False,
            "occupied": False,
            "energy_consumed_kwh": 0.0,
        })

        safe_sensor_id = re.sub(
            r"[^A-Za-z0-9_-]",
            "_",
            room_id
        )

        sensors.append({
            "id": f"TEMP_{safe_sensor_id}",
            "room_id": room_id,
            "sensor_type": "temperature",
            "unit": "celsius",
            "simulated": True,
        })

        rooms_by_floor.setdefault(
            floor_id, []
        ).append(room)

    heating_zones = []

    # Split each floor into simulated heating groups.
    for floor_id, floor_rooms in sorted(
        rooms_by_floor.items()
    ):
        floor_rooms.sort(key=lambda room: room["id"])

        floor_info = floors_map[floor_id]

        for start in range(
            0, len(floor_rooms), ROOMS_PER_ZONE
        ):
            group = floor_rooms[
                start:start + ROOMS_PER_ZONE
            ]

            index = start // ROOMS_PER_ZONE + 1

            zone_id = f"{floor_id}_ZONE_{index}"

            heating_zones.append({
                "id": zone_id,
                "building_id": floor_info["building_id"],
                "floor_id": floor_id,
                "room_ids": [
                    room["id"] for room in group
                ],
                "heating_enabled": False,
                "target_temperature": 21.0,
            })

            for room in group:
                room["heating_zone"] = zone_id

    buildings = sorted(
        buildings_map.values(),
        key=lambda item: item["id"]
    )

    floors = sorted(
        floors_map.values(),
        key=lambda item: (
            item["building_id"],
            item["number"]
        )
    )

    return {
        "buildings.json": buildings,
        "floors.json": floors,
        "rooms.json": rooms,
        "room_states.json": room_states,
        "heating_zones.json": heating_zones,
        "sensors.json": sensors,
    }


def write_json(path, contents):
    path.parent.mkdir(
        parents=True, exist_ok=True
    )

    path.write_text(
        json.dumps(
            contents,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def generate_files(apply=False):
    activities = load_ulbs_activities()
    generated = generate_campus(activities)

    # Always produce preview files first.
    for filename, contents in generated.items():
        write_json(
            GENERATED_DIR / filename,
            contents
        )

    if apply:
        backup_dir = (
            DATA_DIR / "backups" /
            datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )

        backup_dir.mkdir(
            parents=True,
            exist_ok=False
        )

        # Back up existing data before replacing anything.
        for filename in OUTPUT_FILES:
            original = DATA_DIR / filename

            if original.exists():
                shutil.copy2(
                    original,
                    backup_dir / filename
                )

        # Copy validated preview files to active data.
        for filename in OUTPUT_FILES:
            shutil.copy2(
                GENERATED_DIR / filename,
                DATA_DIR / filename
            )

        print("Backup saved to:", backup_dir)
        print("Generated campus activated.")
    else:
        print("Preview generated. Active files unchanged.")

    print("Buildings:", len(generated["buildings.json"]))
    print("Floors:", len(generated["floors.json"]))
    print("Rooms:", len(generated["rooms.json"]))
    print("Heating zones:", len(
        generated["heating_zones.json"]
    ))
    print("Sensors:", len(generated["sensors.json"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Back up and replace active campus JSON files"
    )

    args = parser.parse_args()
    generate_files(apply=args.apply)
