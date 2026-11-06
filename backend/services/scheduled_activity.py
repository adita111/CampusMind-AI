
from pydantic import BaseModel, Field, ConfigDict


class ScheduledActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    room_id: str
    course_name: str
    weekday: int = Field(ge=0, le=6)
    start_time: str
    end_time: str
    group: str = ""
    students_count: int | None = Field(default=None, gt=0)
    activity_type: str = "course"
    required_equipment: list[str] = Field(default_factory=list)
    professor: str | None = None
    is_odd_week: bool = False
    is_even_week: bool = False
    source: str = "ULBS"
    source_schedule_id: int | None = None
    source_slot_id: int | None = None
    formation_ids: list[int] = Field(default_factory=list)
    formation_names: list[str] = Field(default_factory=list)
