"""
BlindVision Backend/Caregiver Layer service.

Section III: "The system maintains a backend service that logs events
(anonymized) with geotags. A caregiver smartphone app shows the user's
current map position (via GPS), configurable geofences, device health
(battery, link), and an alert timeline (SOS, hazards, etc.) for
oversight ... raw images/audio are never transmitted or stored -- only
metadata."

This is a reference implementation: an in-memory store is used for
simplicity; swap `EventStore` for a real database in production. TLS
termination is expected to happen at a reverse proxy in front of this
service (Communication between the Goggles and the backend service is
secured with TLS 1.2, per Section III).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="BlindVision Caregiver Backend", version="0.1.0")


class DeviceEventIn(BaseModel):
    event_type: str
    direction: Optional[str] = None
    distance_m: Optional[float] = None
    severity: str
    timestamp_ms: int
    device_state: str
    source_sensor: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_id: str = "default-user"


class Geofence(BaseModel):
    name: str
    center_lat: float
    center_lon: float
    radius_m: float


class DeviceHealth(BaseModel):
    device_id: str
    battery_pct: float
    link_state: str   # "normal" | "vision_only" | "offline_stick" | "degraded"
    last_seen_ms: int


class EventStore:
    """In-memory store, keyed by device_id. Not persistent -- replace
    with a real datastore for anything beyond local development/demo."""

    def __init__(self) -> None:
        self.events: Dict[str, List[DeviceEventIn]] = {}
        self.geofences: Dict[str, List[Geofence]] = {}
        self.health: Dict[str, DeviceHealth] = {}

    def add_event(self, event: DeviceEventIn) -> None:
        self.events.setdefault(event.device_id, []).append(event)

    def timeline(self, device_id: str, limit: int = 100) -> List[DeviceEventIn]:
        return list(reversed(self.events.get(device_id, [])))[:limit]


store = EventStore()


@app.post("/api/v1/events")
def ingest_event(event: DeviceEventIn) -> dict:
    """Anonymized event ingestion. No raw images or audio accepted --
    the schema simply has no field for them (privacy-by-design)."""
    store.add_event(event)
    return {"status": "accepted", "event_type": event.event_type}


@app.get("/api/v1/events/{device_id}", response_model=List[DeviceEventIn])
def get_timeline(device_id: str, limit: int = 100) -> List[DeviceEventIn]:
    return store.timeline(device_id, limit)


@app.post("/api/v1/geofences/{device_id}")
def add_geofence(device_id: str, geofence: Geofence) -> dict:
    store.geofences.setdefault(device_id, []).append(geofence)
    return {"status": "added", "count": len(store.geofences[device_id])}


@app.get("/api/v1/geofences/{device_id}", response_model=List[Geofence])
def list_geofences(device_id: str) -> List[Geofence]:
    return store.geofences.get(device_id, [])


@app.post("/api/v1/health/{device_id}")
def update_health(device_id: str, battery_pct: float, link_state: str) -> dict:
    store.health[device_id] = DeviceHealth(
        device_id=device_id,
        battery_pct=battery_pct,
        link_state=link_state,
        last_seen_ms=int(time.time() * 1000),
    )
    return {"status": "updated"}


@app.get("/api/v1/health/{device_id}", response_model=DeviceHealth)
def get_health(device_id: str) -> DeviceHealth:
    if device_id not in store.health:
        raise HTTPException(status_code=404, detail="No health data for this device yet.")
    return store.health[device_id]


@app.get("/health")
def liveness() -> dict:
    return {"status": "ok"}
