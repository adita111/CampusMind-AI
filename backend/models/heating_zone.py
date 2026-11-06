
from pydantic import BaseModel, Field


class HeatingZone(BaseModel):
    id: str
    building_id: str
    floor_id: str
    room_ids: list[str] = Field(default_factory=list)

    heating_enabled: bool = False
    target_temperature: float = 21.0
