
from pydantic import BaseModel


class Sensor(BaseModel):
    id: str
    room_id: str
    sensor_type: str
    unit: str
    simulated: bool = True


class SensorReading(BaseModel):
    sensor_id: str
    room_id: str
    value: float
    unit: str
    simulated: bool
