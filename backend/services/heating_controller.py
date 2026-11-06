
from datetime import datetime, timedelta

from services.thermal_service import calculate_next_temperature


def predict_heating_start(
    room,
    current_temperature: float,
    outside_temperature: float,
    course_start: datetime,
    target_temperature: float = 21.0
):
    now = datetime.now()
    remaining_minutes = max(
        0, int((course_start - now).total_seconds() / 60)
    )

    heating_minutes = 0
    predicted_temperature = current_temperature

    while predicted_temperature < target_temperature:
        predicted_temperature = calculate_next_temperature(
            current_temp=predicted_temperature,
            outside_temp=outside_temperature,
            heating_on=True,
            heating_power=room.heating_power,
            heat_loss_coefficient=room.heat_loss_coefficient,
            thermal_capacity=room.thermal_capacity,
            minutes=5
        )

        heating_minutes += 5

        if heating_minutes > 1440:
            return {
                "status": "unreachable",
                "message": "Target temperature cannot be reached"
            }

    start_time = course_start - timedelta(minutes=heating_minutes)

    return {
        "room_id": room.id,
        "current_temperature": current_temperature,
        "target_temperature": target_temperature,
        "heating_duration_minutes": heating_minutes,
        "heating_start_time": start_time.isoformat(),
        "course_start_time": course_start.isoformat(),
        "remaining_minutes": remaining_minutes,
        "should_start_now": datetime.now() >= start_time
    }
