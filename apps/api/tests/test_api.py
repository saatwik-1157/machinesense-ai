"""Behaviour tests for the MachineSense AI FastAPI app (apps/api/main.py)."""
import pytest

import ml
from simulator import FAULT_PROFILES, SENSORS

MACHINE_IDS = ["M-001", "M-002", "M-003", "M-004", "M-005", "M-006"]
SUMMARY_KEYS = {"id", "name", "type", "location", "running", "health", "band", "fault", "runtime_hours"}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def test_root_serves_dashboard(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "MachineSense AI" in r.text
    assert 'src="app.js"' in r.text


@pytest.mark.parametrize("asset", ["app.js", "charts.js", "simulator.js", "styles.css"])
def test_static_assets_are_served(client, asset):
    assert client.get(f"/{asset}").status_code == 200


# ---------------------------------------------------------------------------
# Read-only routes
# ---------------------------------------------------------------------------
def test_overview(client):
    r = client.get("/api/overview")
    assert r.status_code == 200
    body = r.json()
    assert {"fleet_size", "avg_health", "machines_at_risk", "active_alerts",
            "running", "energy", "machines"} <= body.keys()
    assert body["fleet_size"] == 6
    assert body["running"] == 6
    assert set(body["energy"]) == {"monthly_cost_inr", "potential_monthly_savings_inr", "co2_kg_month"}
    assert len(body["machines"]) == 6
    assert 0 <= body["avg_health"] <= 100


def test_list_machines(client):
    r = client.get("/api/machines")
    assert r.status_code == 200
    machines = r.json()
    assert [m["id"] for m in machines] == MACHINE_IDS
    for m in machines:
        assert set(m) == SUMMARY_KEYS


def test_seeded_faults_are_visible(client):
    by_id = {m["id"]: m for m in client.get("/api/machines").json()}
    assert by_id["M-002"]["fault"] == "Bearing Wear"
    assert by_id["M-005"]["fault"] == "Overheating"
    assert by_id["M-001"]["fault"] is None


@pytest.mark.parametrize("machine_id", MACHINE_IDS)
def test_machine_detail(client, machine_id):
    r = client.get(f"/api/machines/{machine_id}")
    assert r.status_code == 200
    body = r.json()
    assert SUMMARY_KEYS | {"sensors", "reading", "prediction", "explanation",
                           "anomalies", "energy", "recommendations"} <= body.keys()
    assert body["id"] == machine_id
    assert set(body["sensors"]) == set(SENSORS)
    for cfg in body["sensors"].values():
        assert {"value", "unit", "baseline", "warn", "critical"} <= cfg.keys()
    assert {"current_health", "rul_hours", "rul_days", "failure_probability",
            "confidence"} <= body["prediction"].keys()


def test_history_default_and_limit(client):
    r = client.get("/api/machines/M-001/history")
    assert r.status_code == 200
    body = r.json()
    assert body["machine_id"] == "M-001"
    assert len(body["points"]) == 60
    assert {"t", "health", *SENSORS} <= body["points"][0].keys()

    assert len(client.get("/api/machines/M-001/history?n=10").json()["points"]) == 10


@pytest.mark.parametrize("n", [0, 241])
def test_history_rejects_out_of_range_n(client, n):
    assert client.get(f"/api/machines/M-001/history?n={n}").status_code == 422


def test_alerts(client):
    r = client.get("/api/alerts")
    assert r.status_code == 200
    alerts = r.json()
    assert isinstance(alerts, list)
    # M-002 is seeded with bearing wear at 50% severity, so there is something to report.
    assert alerts, "expected at least one alert from the seeded faults"
    for a in alerts:
        assert {"machine_id", "machine_name", "sensor", "value", "unit",
                "severity", "kind", "level", "message"} <= a.keys()
    severities = [a["severity"] for a in alerts]
    assert severities == sorted(severities, reverse=True)


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert set(body["sensors"]) == set(SENSORS)
    assert body["faults"] == {k: v["label"] for k, v in FAULT_PROFILES.items()}
    assert body["twin_actions"] == ml.TWIN_ACTIONS


# ---------------------------------------------------------------------------
# Unknown machine -> 404 on every per-machine route
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("method, path, payload", [
    ("get", "/api/machines/NOPE", None),
    ("get", "/api/machines/NOPE/history", None),
    ("post", "/api/machines/NOPE/twin", {"action": "no_action"}),
    ("post", "/api/machines/NOPE/inject-fault", {"fault": "overheating"}),
    ("post", "/api/machines/NOPE/repair", None),
    ("post", "/api/machines/NOPE/power", {"running": False}),
])
def test_unknown_machine_is_404(client, method, path, payload):
    kwargs = {"json": payload} if payload is not None else {}
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Digital twin
# ---------------------------------------------------------------------------
def test_twin_bad_action_is_400(client):
    r = client.post("/api/machines/M-001/twin", json={"action": "sacrifice_a_goat"})
    assert r.status_code == 400
    assert "Unknown twin action" in r.json()["detail"]


@pytest.mark.parametrize("action", ml.TWIN_ACTIONS)
def test_twin_projection(client, fleet, action):
    before_health = fleet.machines["M-002"].true_health
    r = client.post("/api/machines/M-002/twin", json={"action": action})
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == action
    for side in ("before", "after"):
        assert {"health", "rul_hours", "failure_probability", "readings"} <= body[side].keys()
    assert {"health", "rul_hours", "monthly_energy_savings_inr"} <= body["delta"].keys()
    # Every modelled action only shrinks deviations, so projected health never drops.
    assert body["delta"]["health"] >= 0
    # The twin is a what-if: the real asset is untouched.
    assert fleet.machines["M-002"].true_health == before_health


def test_twin_no_action_changes_nothing(client):
    body = client.post("/api/machines/M-002/twin", json={"action": "no_action"}).json()
    assert body["delta"]["health"] == 0
    assert body["after"]["readings"] == {s: body["before"]["readings"][s] for s in SENSORS}


def test_twin_bearing_replacement_helps_bearing_fault(client):
    body = client.post("/api/machines/M-002/twin", json={"action": "bearing_replacement"}).json()
    assert body["delta"]["health"] > 0
    assert body["after"]["readings"]["vibration"] < body["before"]["readings"]["vibration"]


# ---------------------------------------------------------------------------
# Demo controls: inject-fault, repair, power
# ---------------------------------------------------------------------------
def test_inject_fault(client, fleet):
    r = client.post("/api/machines/M-001/inject-fault", json={"fault": "misalignment"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "machine_id": "M-001", "fault": "misalignment"}
    m = fleet.machines["M-001"]
    assert m.fault == "misalignment"
    assert m.fault_severity >= 0.25
    assert client.get("/api/machines/M-001").json()["fault"] == "Shaft Misalignment"


def test_inject_fault_keeps_higher_existing_severity(client, fleet):
    fleet.machines["M-002"].fault_severity = 0.7
    client.post("/api/machines/M-002/inject-fault", json={"fault": "overheating"})
    assert fleet.machines["M-002"].fault == "overheating"
    assert fleet.machines["M-002"].fault_severity == 0.7


def test_inject_unknown_fault_is_400(client, fleet):
    r = client.post("/api/machines/M-001/inject-fault", json={"fault": "gremlins"})
    assert r.status_code == 400
    assert fleet.machines["M-001"].fault is None


def test_inject_fault_requires_body(client):
    assert client.post("/api/machines/M-001/inject-fault", json={}).status_code == 422


def test_repair_clears_fault_and_restores_health(client, fleet):
    m = fleet.machines["M-002"]
    assert m.fault == "bearing_wear"
    r = client.post("/api/machines/M-002/repair")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "machine_id": "M-002"}
    assert m.fault is None
    assert m.fault_severity == 0.0
    assert 0.90 <= m.true_health <= 0.99
    assert client.get("/api/machines/M-002").json()["fault"] is None


def test_power_off_and_on(client, fleet):
    r = client.post("/api/machines/M-003/power", json={"running": False})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "machine_id": "M-003", "running": False}
    assert fleet.machines["M-003"].running is False
    assert client.get("/api/overview").json()["running"] == 5

    fleet.tick()  # a stopped machine records an idle (all-zero) reading
    detail = client.get("/api/machines/M-003").json()
    assert detail["running"] is False
    assert detail["reading"]["running"] is False
    assert detail["reading"]["vibration"] == 0.0

    client.post("/api/machines/M-003/power", json={"running": True})
    assert fleet.machines["M-003"].running is True
    assert client.get("/api/overview").json()["running"] == 6


def test_stopped_faulty_machine_keeps_its_diagnosis(client, fleet):
    """Idle readings are all zeros; health must come from the last running reading."""
    health_running = client.get("/api/machines/M-002").json()["health"]
    client.post("/api/machines/M-002/power", json={"running": False})
    for _ in range(3):
        fleet.tick()
    detail = client.get("/api/machines/M-002").json()
    assert detail["health"] == health_running
    assert detail["health"] < 100
    assert detail["fault"] == "Bearing Wear"

    # History carries the last running health forward through the idle stretch.
    points = client.get("/api/machines/M-002/history").json()["points"]
    assert [p["health"] for p in points[-3:]] == [health_running] * 3


def test_history_window_opening_mid_stop_does_not_score_100(client, fleet):
    """Regression: a window made only of idle readings used to report health 100."""
    health_running = client.get("/api/machines/M-002").json()["health"]
    client.post("/api/machines/M-002/power", json={"running": False})
    for _ in range(3):
        fleet.tick()
    points = client.get("/api/machines/M-002/history?n=3").json()["points"]
    assert [p["health"] for p in points] == [health_running] * 3


def test_power_requires_boolean(client):
    assert client.post("/api/machines/M-001/power", json={"running": "sideways"}).status_code == 422
