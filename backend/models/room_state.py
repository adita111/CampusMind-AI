
from pydantic import BaseModel, Field


class RoomState(BaseModel):
    room_id: str
    current_temperature: float
    target_temperature: float = 21.0
    heating_on: bool = False
    lights_on: bool = False
    occupied: bool = False
    energy_consumed_kwh: float = Field(default=0.0, ge=0)


class SimulationRequest(BaseModel):
    outside_temperature: float
    heating_on: bool
    minutes: int = Field(default=5, gt=0, le=1440)
