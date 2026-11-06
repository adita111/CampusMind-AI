
from datetime import time

from services.room_service import (
    get_all_rooms,
    get_all_states
)
from services.schedule_service import get_all_activities
from services.campus_service import get_heating_zones
from services.schedule_optimizer import optimize_schedule
from services.thermal_service import calculate_next_temperature


STEP_MINUTES = 15
COMFORT_TEMP = 21.0
ECO_TEMP = 16.0
PREHEAT_MINUTES = 90
LIGHTING_W_PER_M2 = 10.0


def to_minutes(value):
    parsed = time.fromisoformat(value)
    return parsed.hour * 60 + parsed.minute


def activity_value(activity, field):
    if isinstance(activity, dict):
        return activity[field]

    return getattr(activity, field)


def room_occupied(room_id, minute, activities, weekday):
    return any(
        activity_value(a, "room_id") == room_id
        and activity_value(a, "weekday") == weekday
        and to_minutes(activity_value(a, "start_time")) <= minute
        < to_minutes(activity_value(a, "end_time"))
        for a in activities
    )


def room_needed_soon(room_id, minute, activities, weekday):
    return any(
        activity_value(a, "room_id") == room_id
        and activity_value(a, "weekday") == weekday
        and minute <= to_minutes(activity_value(a, "start_time"))
        < minute + PREHEAT_MINUTES
        for a in activities
    )


def simulate_scenario(
    scenario_name,
    activities,
    outside_temperature,
    weekday,
    smart_control
):
    rooms = get_all_rooms()
    states = get_all_states()
    zones = get_heating_zones()

    temperatures = {
        state.room_id: state.current_temperature
        for state in states
    }

    room_map = {
        room.id: room
        for room in rooms
        if room.id in temperatures
    }

    heating_energy = 0.0
    lighting_energy = 0.0
    discomfort_minutes = 0
    occupied_room_minutes = 0
    history = []

    zone_states = {
        zone.id: False for zone in zones
    }

    for minute in range(0, 1440, STEP_MINUTES):
        current_time = (
            f"{minute // 60:02d}:"
            f"{minute % 60:02d}"
        )

        for zone in zones:
            zone_rooms = [
                room_map[room_id]
                for room_id in zone.room_ids
                if room_id in room_map
            ]

            if not zone_rooms:
                continue

            if smart_control:
                needed_rooms = [
                    room for room in zone_rooms
                    if room_occupied(
                        room.id, minute, activities, weekday
                    )
                    or room_needed_soon(
                        room.id, minute, activities, weekday
                    )
                ]

                target = (
                    COMFORT_TEMP
                    if needed_rooms
                    else ECO_TEMP
                )

                relevant_rooms = (
                    needed_rooms if needed_rooms
                    else zone_rooms
                )

                lowest_temp = min(
                    temperatures[room.id]
                    for room in relevant_rooms
                )

                if lowest_temp < target - 0.5:
                    zone_states[zone.id] = True
                elif lowest_temp >= target + 0.5:
                    zone_states[zone.id] = False

                heating_on = zone_states[zone.id]

            else:
                heating_on = 360 <= minute < 1080

            for room in zone_rooms:
                old_temp = temperatures[room.id]

                occupied = room_occupied(
                    room.id, minute, activities, weekday
                )

                # Evaluate comfort at the start of the interval
                if occupied:
                    occupied_room_minutes += STEP_MINUTES

                    if old_temp < COMFORT_TEMP - 0.5:
                        discomfort_minutes += STEP_MINUTES

                next_temp = calculate_next_temperature(
                    current_temp=old_temp,
                    outside_temp=outside_temperature,
                    heating_on=heating_on,
                    heating_power=room.heating_power,
                    heat_loss_coefficient=room.heat_loss_coefficient,
                    thermal_capacity=room.thermal_capacity,
                    minutes=STEP_MINUTES
                )

                temperatures[room.id] = next_temp

                if heating_on:
                    heating_energy += (
                        room.heating_power / 1000
                        * STEP_MINUTES / 60
                    )

                # Smart: lights follow the schedule
                # Baseline: lights follow a fixed program
                lights_on = (
                    occupied if smart_control
                    else 360 <= minute < 1080
                )

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
                    "temperature": next_temp,
                    "heating_on": heating_on,
                    "lights_on": lights_on,
                    "occupied": occupied
                })

    comfort_percentage = (
        100 * (
            1 - discomfort_minutes / occupied_room_minutes
        )
        if occupied_room_minutes > 0
        else 100.0
    )

    return {
        "scenario": scenario_name,
        "heating_kwh_thermal": round(heating_energy, 2),
        "lighting_kwh_electric": round(lighting_energy, 2),
        "discomfort_minutes": discomfort_minutes,
        "occupied_room_minutes": occupied_room_minutes,
        "comfort_percentage": round(comfort_percentage, 2),
        "history": history
    }


def compare_energy(outside_temperature=-3.0, weekday=0):
    original_activities = get_all_activities()

    optimized = optimize_schedule()
    optimized_activities = optimized["activities"]

    baseline = simulate_scenario(
        "baseline",
        original_activities,
        outside_temperature,
        weekday,
        smart_control=False
    )

    smart = simulate_scenario(
        "smart_control",
        original_activities,
        outside_temperature,
        weekday,
        smart_control=True
    )

    optimized_smart = simulate_scenario(
        "optimized_smart",
        optimized_activities,
        outside_temperature,
        weekday,
        smart_control=True
    )

    # Compare thermal heating energy separately
    baseline_heating = baseline["heating_kwh_thermal"]

    savings_percent = (
        100 * (
            baseline_heating
            - optimized_smart["heating_kwh_thermal"]
        ) / baseline_heating
        if baseline_heating > 0
        else 0
    )

    return {
        "outside_temperature": outside_temperature,
        "weekday": weekday,
        "baseline": baseline,
        "smart_control": smart,
        "optimized_smart": optimized_smart,
        "heating_savings_percent": round(
            savings_percent, 2
        ),
        "schedule_optimization": {
            "moved_activities": optimized["moved_activities"],
            "original_zone_count": optimized["original_zone_count"],
            "optimized_zone_count": optimized["optimized_zone_count"]
        }
    }
