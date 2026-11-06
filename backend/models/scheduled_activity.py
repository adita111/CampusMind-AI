
from pydantic import BaseModel, Field


class ScheduledActivity(BaseModel):
    id: str
    room_id: str
    course_name: str
    weekday: int = Field(ge=0, le=6)
    start_time: str
    end_time: str
    group: str
    students_count: int = Field(gt=0)
    activity_type: str
    required_equipment: list[str] = Field(default_factory=list)
