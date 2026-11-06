
import json
from pathlib import Path

from models.sensor import Sensor, SensorReading
from services.temperature_generator_mock import get_generated_temperature


SENSORS_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "generated"
    / "sensors.json"
)


def get_all_sensors() -> list[Sensor]:
    with open(SENSORS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [Sensor(**item) for item in data]


def get_sensor_by_id(sensor_id: str) -> Sensor | None:
    for sensor in get_all_sensors():
        if sensor.id == sensor_id:
            return sensor

    return None


def get_sensors_by_room(room_id: str) -> list[Sensor]:
    return [
        sensor
        for sensor in get_all_sensors()
        if sensor.room_id == room_id
    ]


def get_sensor_reading(sensor_id: str) -> SensorReading | None:
    sensor = get_sensor_by_id(sensor_id)

    if sensor is None:
        return None

    if sensor.sensor_type != "temperature":
        return None

    temperature = get_generated_temperature(sensor.room_id)

    if temperature is None:
        return None

    return SensorReading(
        sensor_id=sensor.id,
        room_id=sensor.room_id,
        value=temperature,
        unit=sensor.unit,
        simulated=sensor.simulated
    )

