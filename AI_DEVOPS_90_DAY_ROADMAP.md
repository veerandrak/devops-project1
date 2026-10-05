# 90-Day AI + DevOps Engineering Roadmap

Goal: move from Cloud/DevOps engineering into AI Platform, LLMOps, MLOps and Generative AI engineering by building production-style evidence instead of collecting many certificates.

## Days 1-10 — AI-ready Python
Focus on FastAPI, Pydantic, async Python, REST APIs, JSON contracts, pytest, environment variables, logging and error handling.

Deliverable: a tested FastAPI service with structured request/response models and Docker support.

## Days 11-25 — LLM engineering
Learn transformers at a practical level, tokens/context windows, prompting, structured outputs, tool calling, embeddings and inference tradeoffs.

Deliverable: add a provider interface to the incident service so an LLM can summarize evidence into a strict schema without giving the model direct execution privileges.

## Days 26-40 — RAG
Learn chunking, metadata, embeddings, vector databases, hybrid retrieval, reranking, citations and evaluation.

Deliverable: ingest runbooks and retrieve the most relevant evidence for each incident. Compare lexical retrieval against embedding-based retrieval and record evaluation results.

## Days 41-55 — Agents
Learn tools, state, memory, planning, approval gates, retries, idempotency and multi-step workflows.

Deliverable: turn the incident triage service into an agent that can inspect read-only evidence from logs, deployments and runbooks, then propose actions. Destructive actions remain behind human approval.

## Days 56-70 — LLMOps / AI DevOps
Use Docker, Kubernetes, Terraform, CI/CD, secrets, observability, tracing, latency budgets, caching, cost controls and security.

Deliverable: deploy the service with health checks, resource limits, CI tests, deployment manifests, telemetry and rollback notes.

## Days 71-90 — Portfolio proof
Finish 2-3 strong projects, deploy or reproduce them, add evaluation, write architecture docs, capture limitations, and publish concise GitHub/LinkedIn evidence.

Primary projects:
1. AI DevOps Incident Agent
2. Production RAG Platform
3. AI CloudOps Agent

## Weekly evidence rule
Every week should produce something reviewable: code, tests, an evaluation result, deployment evidence, an architecture decision, or a short write-up. Avoid claims that are not backed by repository evidence.
