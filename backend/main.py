
from fastapi import FastAPI, HTTPException

from models.room import Room
from models.building import Building, Floor
from models.heating_zone import HeatingZone
from models.room_state import RoomState, SimulationRequest

import httpx
from services.weather_service import get_weather_forecast

from datetime import datetime
from services.heating_controller import predict_heating_start

from services.room_service import (
    get_all_rooms,
    get_room_by_id,
    get_room_state,
    update_room_state
)
from services.campus_service import (
    get_buildings,
    get_floors,
    get_heating_zones,
    get_rooms_on_floor
)

from models.scheduled_activity import ScheduledActivity
from services.schedule_service import (
    get_all_activities,
    get_room_schedule
)

from services.thermal_service import calculate_next_temperature


app = FastAPI(
    title="CampusMind AI",
    description="AI-powered energy optimization system",
    version="0.2.0"
)


@app.get("/")
def home():
    return {"message": "Welcome to CampusMind AI!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rooms", response_model=list[Room])
def get_rooms():
    return get_all_rooms()


@app.get("/rooms/{room_id}", response_model=Room)
def get_room(room_id: str):
    room = get_room_by_id(room_id)

    if room is None:
        raise HTTPException(404, "Room not found")

    return room


@app.get("/rooms/{room_id}/state", response_model=RoomState)
def get_state(room_id: str):
    state = get_room_state(room_id)

    if state is None:
        raise HTTPException(404, "Room state not found")

    return state


@app.post("/rooms/{room_id}/simulate", response_model=RoomState)
def simulate_room(room_id: str, request: SimulationRequest):
    room = get_room_by_id(room_id)
    state = get_room_state(room_id)

    if room is None or state is None:
        raise HTTPException(404, "Room not found")

    new_temperature = calculate_next_temperature(
        current_temp=state.current_temperature,
        outside_temp=request.outside_temperature,
        heating_on=request.heating_on,
        heating_power=room.heating_power,
        heat_loss_coefficient=room.heat_loss_coefficient,
        thermal_capacity=room.thermal_capacity,
        minutes=request.minutes
    )

    state.current_temperature = new_temperature
    state.heating_on = request.heating_on

    if request.heating_on:
        state.energy_consumed_kwh += (
            room.heating_power / 1000
        ) * (request.minutes / 60)

    update_room_state(state)

    return state


@app.get("/schedule", response_model=list[ScheduledActivity])
def get_schedule():
    return get_all_activities()


@app.get(
    "/rooms/{room_id}/schedule",
    response_model=list[ScheduledActivity]
)
def get_schedule_for_room(room_id: str):

    room = get_room_by_id(room_id)

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found"
        )

    return get_room_schedule(room_id)


@app.get("/weather/forecast")
def weather_forecast():
    try:
        forecast = get_weather_forecast()

        return {
            "city": "Sibiu",
            "forecast": forecast
        }

    except (httpx.HTTPError, KeyError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="Weather service unavailable"
        ) from error


@app.get("/rooms/{room_id}/heating/predict")
def predict_room_heating(
    room_id: str,
    course_start: datetime,
    outside_temperature: float = -3.0
):
    room = get_room_by_id(room_id)
    state = get_room_state(room_id)

    if room is None or state is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found"
        )

    result = predict_heating_start(
        room=room,
        current_temperature=state.current_temperature,
        outside_temperature=outside_temperature,
        course_start=course_start,
        target_temperature=state.target_temperature
    )

    return result


@app.get("/buildings", response_model=list[Building])
def list_buildings():
    return get_buildings()


@app.get("/buildings/{building_id}/floors", response_model=list[Floor])
def list_floors(building_id: str):
    if not any(b.id == building_id for b in get_buildings()):
        raise HTTPException(404, "Building not found")

    return get_floors(building_id)


@app.get("/buildings/{building_id}/floors/{floor_number}/rooms",
         response_model=list[Room])
def list_rooms_on_floor(building_id: str, floor_number: int):
    floors = get_floors(building_id)

    if not any(f.number == floor_number for f in floors):
        raise HTTPException(404, "Floor not found")

    return get_rooms_on_floor(building_id, floor_number)


@app.get("/heating-zones", response_model=list[HeatingZone])
def list_heating_zones():
    return get_heating_zones()
