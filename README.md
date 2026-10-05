# Sai Veerandra Kurakula — Cloud, DevOps & SRE Portfolio

[![Portfolio CI](https://github.com/veerandrak/devops-project1/actions/workflows/ci.yml/badge.svg)](https://github.com/veerandrak/devops-project1/actions/workflows/ci.yml) [![Security Baseline](https://github.com/veerandrak/devops-project1/actions/workflows/security.yml/badge.svg)](https://github.com/veerandrak/devops-project1/actions/workflows/security.yml) [![CodeQL](https://github.com/veerandrak/devops-project1/actions/workflows/codeql.yml/badge.svg)](https://github.com/veerandrak/devops-project1/actions/workflows/codeql.yml)

Engineering portfolio focused on **AWS, Azure, Kubernetes, Terraform, CI/CD, Python, reliability, security and AI-assisted operations**.

The projects here are designed to make engineering decisions reviewable: each one documents its trust boundaries, tests, operational trade-offs and current validation status. No employer source code or unverified production outcomes are presented as portfolio results.

## Start here

| Project | What it demonstrates | Current evidence |
|---|---|---|
| **[AI DevOps Incident Agent](projects/ai-devops-incident-agent)** | FastAPI incident intake, deterministic signal detection, local runbook retrieval, structured triage and a no-execution safety boundary | Runnable API + automated tests |
| **[ReleaseGuard](projects/releaseguard)** | Fail-closed release decisions from telemetry and restore evidence | 14 automated tests + synthetic pass/hold scenarios |
| **[Rotation Rehearsal](projects/rotation-rehearsal)** | Dependency-aware secrets migration planning, capacity constraints and retirement evidence | 15 automated tests + synthetic scenarios |
| **[Kubernetes Reliability Lab](projects/kubernetes-sre-lab)** | Hardened container, Kubernetes probes/policies, Prometheus alerts, Jenkins pipeline and runbook | Python integration tests; deployment steps documented |
| **[AWS Encrypted Backup Lab](projects/aws-encrypted-backup-lab)** | S3/KMS/IAM Terraform, immutable-version restore and SHA-256 integrity verification | Python unit tests; cloud deployment intentionally not claimed |
| **[Azure AKS Platform Lab](projects/azure-aks-platform-lab)** | Private AKS design, Entra RBAC, managed/workload identity and validation pipeline | Terraform/YAML design; cloud deployment intentionally not claimed |

## Flagship: AI DevOps Incident Agent

The first milestone is deliberately deterministic before adding an LLM:

```text
Incident JSON
    |
    v
FastAPI /triage
    |
    +--> signal detector
    |
    +--> local runbook retrieval
    |
    v
structured recommendations
    |
    v
execution_authorized: false
```

This establishes a testable safety boundary before future RAG, LLM summarization, read-only tooling and human approval workflows are introduced.

## Engineering themes

- **Reliability:** health/readiness checks, disruption budgets, rollback thinking, restore evidence and fail-closed gates.
- **Security:** least privilege, KMS encryption, non-root containers, strict input validation, identity-first cloud design and explicit trust boundaries.
- **Automation:** Terraform, Python, Jenkins, Azure Pipelines and GitHub Actions.
- **Operations:** runbooks, failure drills, evidence freshness, reproducibility and cleanup procedures.
- **AI + DevOps:** build deterministic evidence and approval boundaries first; add model reasoning without granting implicit production authority.

## Reproduce the local checks

Python 3.12 is recommended.

```bash
(cd projects/ai-devops-incident-agent && python -m pip install -r requirements-dev.txt && pytest -q)
(cd projects/kubernetes-sre-lab && python -m unittest -v)
(cd projects/aws-encrypted-backup-lab && python -m pip install -r requirements.txt && python -m unittest -v)
(cd projects/releaseguard && python -m unittest -v)
(cd projects/rotation-rehearsal && python -m unittest -v)
```

GitHub Actions runs these checks automatically and also verifies Terraform formatting.

## Reviewer shortcuts

- [Architecture overview](docs/ARCHITECTURE.md)
- [Portfolio evidence matrix](docs/PORTFOLIO_EVIDENCE.md)
- [10-minute reviewer guide](docs/REVIEWER_GUIDE.md)
- [Security policy](SECURITY.md)

## Validation status

This portfolio separates **implemented/tested**, **locally runnable**, and **cloud-deployed** evidence. A README saying something is designed does not make it deployed. Cloud resources, production SLOs, cost savings and compliance outcomes are only claimed when repository evidence supports them.

## Roadmap

See **[AI + DevOps 90-Day Roadmap](AI_DEVOPS_90_DAY_ROADMAP.md)** for the planned progression from deterministic incident triage to RAG, tool calling, approval-gated agents, observability and platform deployment.

## Working style

Future changes should follow **issue → branch → pull request → CI → merge**. See [CONTRIBUTING.md](CONTRIBUTING.md).

---
**Target roles:** Cloud Engineer · DevOps Engineer · SRE · Platform Engineer · AI Platform / LLMOps
