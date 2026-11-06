
def calculate_next_temperature(
    current_temp: float,
    outside_temp: float,
    heating_on: bool,
    heating_power: float,
    heat_loss_coefficient: float,
    thermal_capacity: float,
    minutes: int = 5
) -> float:

    remaining_minutes = minutes
    temperature = current_temp

    while remaining_minutes > 0:
        step_minutes = min(5, remaining_minutes)
        delta_time = step_minutes * 60

        heat_input = heating_power if heating_on else 0

        heat_loss = heat_loss_coefficient * (
            temperature - outside_temp
        )

        temperature_change = (
            (heat_input - heat_loss)
            * delta_time
            / thermal_capacity
        )

        temperature += temperature_change
        remaining_minutes -= step_minutes

    return round(temperature, 3)
