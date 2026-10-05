from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def triage(payload):
    response = client.post("/triage", json=payload)
    assert response.status_code == 200
    return response.json()


def base(**changes):
    payload = {
        "service": "checkout",
        "environment": "staging",
        "title": "Checkout incident",
        "symptoms": [],
        "logs": [],
    }
    payload.update(changes)
    return payload


def test_health():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_database_and_latency_detection():
    result = triage(
        base(
            title="Checkout latency increased",
            symptoms=["p95 latency is high", "database connection timeout"],
            logs=["connection refused while opening database session"],
        )
    )
    names = {item["name"] for item in result["signals"]}
    assert {"database_connectivity", "latency_regression"} <= names
    assert result["execution_authorized"] is False


def test_resource_pressure_detection():
    result = triage(base(symptoms=["pod restarted after OOM"], logs=["memory pressure detected"]))
    assert "resource_pressure" in {item["name"] for item in result["signals"]}


def test_unknown_incident_is_safe():
    result = triage(base(title="Unexpected behavior with no known signature"))
    assert [item["name"] for item in result["signals"]] == ["unclassified"]
    assert result["recommended_actions"]
    assert result["execution_authorized"] is False
