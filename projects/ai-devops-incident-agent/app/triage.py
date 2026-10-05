from .models import IncidentRequest, RunbookMatch, Signal, TriageResponse


RULES = (
    {
        "name": "database_connectivity",
        "keywords": ("database", "db ", "connection refused", "connection timeout", "sql"),
        "runbook": "Database connectivity",
        "guidance": (
            "Confirm the failure is limited to the expected environment and dependency.",
            "Check connection-pool saturation, DNS resolution and database reachability.",
            "Review recent database, network-policy and credential changes before remediation.",
        ),
        "action": "Inspect database reachability, connection-pool pressure and recent dependency changes.",
    },
    {
        "name": "latency_regression",
        "keywords": ("latency", "slow", "timeout", "p95", "p99"),
        "runbook": "Latency regression",
        "guidance": (
            "Compare current latency and error rate with the last known healthy window.",
            "Check saturation signals for CPU, memory, downstream calls and queue depth.",
            "Correlate the regression with the most recent deployment or configuration change.",
        ),
        "action": "Compare latency, saturation and deployment timing before proposing rollback.",
    },
    {
        "name": "resource_pressure",
        "keywords": ("oom", "out of memory", "memory pressure", "cpu thrott", "cpu high", "disk full"),
        "runbook": "Resource pressure",
        "guidance": (
            "Inspect requested versus actual resource usage and recent workload growth.",
            "Check pod restarts, OOM kills, CPU throttling and node pressure.",
            "Avoid increasing limits until the cause and capacity impact are understood.",
        ),
        "action": "Inspect resource saturation, restarts and node pressure before changing limits.",
    },
    {
        "name": "availability",
        "keywords": ("unavailable", "5xx", "crashloop", "not ready", "health check", "readiness"),
        "runbook": "Service availability",
        "guidance": (
            "Check readiness, replica availability and recent rollout status.",
            "Inspect events and logs for failed scheduling, image, configuration or dependency errors.",
            "Prefer a reviewed rollback when a recent change clearly correlates with the outage.",
        ),
        "action": "Inspect readiness, replicas, events and rollout history.",
    },
)


def _evidence_text(incident: IncidentRequest) -> list[str]:
    return [incident.title, *incident.symptoms, *incident.logs]


def triage_incident(incident: IncidentRequest) -> TriageResponse:
    evidence = _evidence_text(incident)
    lowered = [(item, item.lower()) for item in evidence]
    signals: list[Signal] = []
    runbooks: list[RunbookMatch] = []
    actions: list[str] = []

    for rule in RULES:
        matched = [original for original, text in lowered if any(word in text for word in rule["keywords"])]
        if not matched:
            continue
        signals.append(Signal(name=rule["name"], evidence=matched[:5]))
        runbooks.append(
            RunbookMatch(signal=rule["name"], title=rule["runbook"], guidance=list(rule["guidance"]))
        )
        actions.append(rule["action"])

    if not signals:
        signals.append(Signal(name="unclassified", evidence=evidence[:5]))
        runbooks.append(
            RunbookMatch(
                signal="unclassified",
                title="Unknown incident",
                guidance=[
                    "Confirm scope, affected environment and customer impact.",
                    "Collect fresh metrics, logs, events and the last known healthy deployment.",
                    "Escalate to the service owner before making destructive changes.",
                ],
            )
        )
        actions.append("Collect fresh evidence and escalate to the service owner before remediation.")

    return TriageResponse(
        service=incident.service,
        environment=incident.environment,
        signals=signals,
        runbooks=runbooks,
        recommended_actions=list(dict.fromkeys(actions)),
        execution_authorized=False,
    )
