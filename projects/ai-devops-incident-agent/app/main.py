from fastapi import FastAPI

from .models import IncidentRequest, TriageResponse
from .triage import triage_incident

app = FastAPI(
    title="AI DevOps Incident Agent",
    version="0.1.0",
    description="Deterministic incident triage baseline. No remediation is executed.",
)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
def triage(incident: IncidentRequest) -> TriageResponse:
    return triage_incident(incident)
