# AI DevOps Incident Agent

A portfolio project that combines DevOps incident reasoning with an AI-ready service architecture.

The first milestone is deliberately deterministic and testable: it accepts an incident, detects operational signals, retrieves relevant runbook guidance, and returns a structured triage response. Later milestones add LLM summarization, embedding-based RAG, tool calling, approval-gated agent workflows, Kubernetes deployment and observability.

## Why this project
A useful AI operations system should not jump directly from a model response to production changes. This project separates incident evidence, retrieval, reasoning, recommendations and execution approval.

## Current architecture

```text
Incident JSON
    |
    v
FastAPI /triage
    |
    +--> signal detector
    |
    +--> local runbook retriever
    |
    v
structured triage response
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Test

```bash
pytest -q
```

## Safety boundary
This repository does not automatically execute remediation commands. Recommendations are advisory until an explicit, auditable approval layer is added.

## Roadmap
1. Deterministic triage baseline + tests
2. Strict-schema LLM summarization
3. Embedding/vector retrieval and RAG evaluation
4. Read-only operational tools + human approval gates
5. Kubernetes, CI/CD, tracing, metrics, security and cost controls
