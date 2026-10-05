# Reviewer Guide

If you are evaluating this portfolio for a Cloud, DevOps, SRE, Platform or AI Platform role, the quickest path is:

1. **ReleaseGuard** — review the fail-closed decision logic and tests.
2. **AI DevOps Incident Agent** — review the API contract, deterministic triage and explicit no-execution boundary.
3. **Kubernetes Reliability Lab** — review the Dockerfile, deployment security context, probes, disruption budget, network policy and runbook.
4. **AWS Encrypted Backup Lab** — review Terraform least privilege and version-specific integrity-checked restore.
5. **Rotation Rehearsal** — review dependency scheduling, evidence freshness and plan binding.
6. **Azure AKS Platform Lab** — review private API, Entra RBAC and workload-identity design.

## Signals this portfolio is intended to demonstrate

- Can reason about operational failure rather than only provision resources.
- Treats backup restore, rollback and evidence freshness as engineering concerns.
- Separates model recommendations from execution authority.
- Uses tests and strict validation around automation.
- Documents limitations instead of presenting unexecuted designs as production results.

See [PORTFOLIO_EVIDENCE.md](PORTFOLIO_EVIDENCE.md) for the validation matrix and [ARCHITECTURE.md](ARCHITECTURE.md) for the cross-project architecture.
