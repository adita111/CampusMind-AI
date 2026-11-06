
from datetime import time

from services.room_service import (
    get_all_rooms,
    get_all_states
)
from services.schedule_service import get_all_activities
from services.campus_service import get_heating_zones
from services.thermal_service import calculate_next_temperature


STEP_MINUTES = 15
COMFORT_TEMPERATURE = 21.0
ECO_TEMPERATURE = 16.0
PREHEAT_MINUTES = 90

# Assumed lighting power: 10 W per square meter
LIGHTING_W_PER_M2 = 10.0


def time_to_minutes(value: str) -> int:
    parsed = time.fromisoformat(value)
    return parsed.hour * 60 + parsed.minute


def is_occupied(room_id, minute, activities, weekday):
    return any(
        activity.room_id == room_id
        and activity.weekday == weekday
        and time_to_minutes(activity.start_time) <= minute
        < time_to_minutes(activity.end_time)
        for activity in activities
    )


def has_upcoming_course(
    room_id, minute, activities, weekday
):
    return any(
        activity.room_id == room_id
        and activity.weekday == weekday
        and minute <= time_to_minutes(activity.start_time)
        < minute + PREHEAT_MINUTES
        for activity in activities
    )


def simulate_smart_energy(
    outside_temperature: float = -3.0,
    weekday: int = 0
):
    rooms = get_all_rooms()
    states = get_all_states()
    activities = get_all_activities()
    heating_zones = get_heating_zones()

    temperatures = {
        state.room_id: state.current_temperature
        for state in states
    }

    # Only use rooms that have an initial state
    rooms = [
        room for room in rooms
        if room.id in temperatures
    ]

    rooms_by_id = {
        room.id: room for room in rooms
    }

    heating_energy = 0.0
    lighting_energy = 0.0
    history = []

    # Retain the previous heating state for hysteresis
    zone_states = {
        zone.id: False
        for zone in heating_zones
    }

    for minute in range(0, 1440, STEP_MINUTES):
        current_time = (
            f"{minute // 60:02d}:"
            f"{minute % 60:02d}"
        )

        # Decide heating separately for each thermal zone
        for zone in heating_zones:
            zone_rooms = [
                rooms_by_id[room_id]
                for room_id in zone.room_ids
                if room_id in rooms_by_id
            ]

            if not zone_rooms:
                continue

            # Rooms that are occupied or will soon be used
            needed_rooms = [
                room for room in zone_rooms
                if is_occupied(
                    room.id, minute, activities, weekday
                )
                or has_upcoming_course(
                    room.id, minute, activities, weekday
                )
            ]

            if needed_rooms:
                target = COMFORT_TEMPERATURE
                relevant_rooms = needed_rooms
            else:
                target = ECO_TEMPERATURE
                relevant_rooms = zone_rooms

            # Use the coldest relevant room
            lowest_temp = min(
                temperatures[room.id]
                for room in relevant_rooms
            )

            # Thermostat with hysteresis
            if lowest_temp < target - 0.5:
                zone_states[zone.id] = True
            elif lowest_temp >= target + 0.5:
                zone_states[zone.id] = False

            heating_on = zone_states[zone.id]

            # Same heating decision for all rooms in zone
            for room in zone_rooms:
                old_temp = temperatures[room.id]

                new_temp = calculate_next_temperature(
                    current_temp=old_temp,
                    outside_temp=outside_temperature,
                    heating_on=heating_on,
                    heating_power=room.heating_power,
                    heat_loss_coefficient=room.heat_loss_coefficient,
                    thermal_capacity=room.thermal_capacity,
                    minutes=STEP_MINUTES
                )

                temperatures[room.id] = new_temp

                if heating_on:
                    heating_energy += (
                        room.heating_power / 1000
                        * STEP_MINUTES / 60
                    )

                occupied = is_occupied(
                    room.id, minute, activities, weekday
                )

                # Initial lighting rule:
                # ON for scheduled activities, OFF otherwise
                lights_on = occupied

                if lights_on:
                    lighting_energy += (
                        room.area_m2
                        * LIGHTING_W_PER_M2
                        / 1000
                        * STEP_MINUTES / 60
                    )

                history.append({
                    "time": current_time,
                    "room_id": room.id,
                    "heating_zone": zone.id,
                    "temperature": new_temp,
                    "heating_on": heating_on,
                    "lights_on": lights_on,
                    "occupied": occupied,
                    "target_temperature": target
                })

    return {
        "scenario": "smart_control",
        "weekday": weekday,
        "outside_temperature": outside_temperature,
        "total_heating_kwh": round(heating_energy, 2),
        "total_lighting_kwh": round(lighting_energy, 2),
        "final_temperatures": temperatures,
        "history": history
    }
