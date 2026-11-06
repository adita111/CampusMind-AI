
from services.room_service import (
    get_all_rooms,
    get_all_states
)

from services.thermal_service import (
    calculate_next_temperature
)


def simulate_energy(
    outside_temperature: float = -3.0
):
    rooms = get_all_rooms()
    states = get_all_states()

    # Make a copy of the initial temperatures
    temperatures = {
        state.room_id: state.current_temperature
        for state in states
    }

    total_energy_kwh = 0.0
    history = []

    # Simulate one day in 15-minute steps
    for minute in range(0, 1440, 15):

        hour = minute // 60
        minutes = minute % 60

        current_time = f"{hour:02d}:{minutes:02d}"

        # Basic fixed heating schedule
        heating_on = 6 <= hour < 18

        for room in rooms:

            current_temperature = temperatures[room.id]

            next_temperature = calculate_next_temperature(
                current_temp=current_temperature,
                outside_temp=outside_temperature,
                heating_on=heating_on,
                heating_power=room.heating_power,
                heat_loss_coefficient=room.heat_loss_coefficient,
                thermal_capacity=room.thermal_capacity,
                minutes=15
            )

            temperatures[room.id] = next_temperature

            # Thermal energy, not electricity
            if heating_on:
                energy = (
                    room.heating_power / 1000
                ) * (15 / 60)

                total_energy_kwh += energy

            history.append({
                "time": current_time,
                "room_id": room.id,
                "temperature": next_temperature,
                "heating_on": heating_on
            })

    return {
        "scenario": "fixed_schedule",
        "outside_temperature": outside_temperature,
        "total_thermal_energy_kwh": round(
            total_energy_kwh, 2
        ),
        "final_temperatures": temperatures,
        "history": history
    }
