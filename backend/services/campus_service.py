
import json
from pathlib import Path

from models.building import Building, Floor
from models.heating_zone import HeatingZone
from services.room_service import get_all_rooms


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def get_buildings() -> list[Building]:
    return [
        Building(**item)
        for item in load_json("buildings.json")
    ]


def get_floors(building_id: str) -> list[Floor]:
    floors = [
        Floor(**item)
        for item in load_json("floors.json")
    ]

    return [
        floor
        for floor in floors
        if floor.building_id == building_id
    ]


def get_heating_zones() -> list[HeatingZone]:
    return [
        HeatingZone(**item)
        for item in load_json("heating_zones.json")
    ]


def get_rooms_on_floor(
    building_id: str,
    floor_number: int
):
    return [
        room
        for room in get_all_rooms()
        if room.building == building_id
        and room.floor == floor_number
    ]
