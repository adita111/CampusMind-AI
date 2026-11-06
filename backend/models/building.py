
from pydantic import BaseModel, Field


class Building(BaseModel):
    id: str
    name: str
    address: str | None = None


class Floor(BaseModel):
    id: str
    building_id: str
    number: int
    name: str | None = None
