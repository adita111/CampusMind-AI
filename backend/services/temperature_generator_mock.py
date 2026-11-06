
import json
import random
import time
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "room_states.json"
)

UPDATE_INTERVAL = 10
MAX_CHANGE = 0.2
MAX_DEVIATION = 2.0


def load_initial_temperatures():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        states = json.load(file)

    return {
        state["room_id"]: float(state["current_temperature"])
        for state in states
    }


initial_temperatures = load_initial_temperatures()

# Current simulated temperature for each room
current_temperatures = initial_temperatures.copy()

# Time of the last generated update
last_update = time.monotonic()


def update_temperatures():
    global last_update

    now = time.monotonic()

    elapsed_intervals = int(
        (now - last_update) // UPDATE_INTERVAL
    )

    if elapsed_intervals <= 0:
        return

    # Generate one random change per elapsed interval
    for _ in range(elapsed_intervals):

        for room_id, current_temp in current_temperatures.items():

            initial_temp = initial_temperatures[room_id]

            change = random.randint(
                round(-MAX_CHANGE * 10),
                round(MAX_CHANGE * 10)
            ) / 10

            new_temp = round(current_temp + change, 1)

            minimum = initial_temp - MAX_DEVIATION
            maximum = initial_temp + MAX_DEVIATION

            new_temp = max(
                minimum,
                min(maximum, new_temp)
            )

            current_temperatures[room_id] = round(
                new_temp,
                2
            )

    last_update += elapsed_intervals * UPDATE_INTERVAL


def get_generated_temperature(room_id: str):
    update_temperatures()

    return current_temperatures.get(room_id)
