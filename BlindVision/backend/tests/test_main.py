from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_event_ingest_and_timeline():
    event = {
        "event_type": "CRITICAL_OBSTACLE",
        "direction": "front",
        "distance_m": 0.4,
        "severity": "CRITICAL_OBSTACLE",
        "timestamp_ms": 1234567890,
        "device_state": "normal",
        "source_sensor": "stick",
        "device_id": "user-1",
    }
    resp = client.post("/api/v1/events", json=event)
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    resp = client.get("/api/v1/events/user-1")
    assert resp.status_code == 200
    timeline = resp.json()
    assert len(timeline) == 1
    assert timeline[0]["event_type"] == "CRITICAL_OBSTACLE"
    # no raw image/audio field exists on the schema at all
    assert "image" not in timeline[0]
    assert "audio" not in timeline[0]


def test_geofence_roundtrip():
    geofence = {"name": "home", "center_lat": 24.86, "center_lon": 67.00, "radius_m": 150}
    resp = client.post("/api/v1/geofences/user-2", json=geofence)
    assert resp.status_code == 200

    resp = client.get("/api/v1/geofences/user-2")
    assert resp.status_code == 200
    fences = resp.json()
    assert len(fences) == 1
    assert fences[0]["name"] == "home"


def test_health_endpoint_requires_prior_update():
    resp = client.get("/api/v1/health/never-seen-device")
    assert resp.status_code == 404

    resp = client.post("/api/v1/health/user-3?battery_pct=87.5&link_state=normal")
    assert resp.status_code == 200

    resp = client.get("/api/v1/health/user-3")
    assert resp.status_code == 200
    assert resp.json()["battery_pct"] == 87.5
