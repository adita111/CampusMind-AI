
from pydantic import BaseModel, Field


class Room(BaseModel):
    id: str
    building: str
    floor: int
    area_m2: float = Field(gt=0)
    capacity: int = Field(gt=0)
    room_type: str
    equipment: list[str]
    heating_zone: str


    heat_loss_coefficient: float = Field(ge=0)
    thermal_capacity: float = Field(gt=0)
    heating_power: float = Field(ge=0)
