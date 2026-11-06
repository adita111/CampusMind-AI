
import json
from pathlib import Path

from models.room import Room
from models.room_state import RoomState


DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"

ROOMS_FILE = DATA_DIRECTORY / "rooms.json"
STATES_FILE = DATA_DIRECTORY / "room_states.json"


def get_all_rooms() -> list[Room]:
    with open(ROOMS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [Room(**room) for room in data]


def get_room_by_id(room_id: str) -> Room | None:
    for room in get_all_rooms():
        if room.id == room_id:
            return room

    return None


def get_all_states() -> list[RoomState]:
    with open(STATES_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [RoomState(**state) for state in data]


def get_room_state(room_id: str) -> RoomState | None:
    for state in get_all_states():
        if state.room_id == room_id:
            return state

    return None


def update_room_state(updated_state: RoomState) -> None:
    states = get_all_states()

    for index, state in enumerate(states):
        if state.room_id == updated_state.room_id:
            states[index] = updated_state
            break
    else:
        raise ValueError("Room state not found")

    with open(STATES_FILE, "w", encoding="utf-8") as file:
        json.dump(
            [state.model_dump() for state in states],
            file,
            indent=2
        )