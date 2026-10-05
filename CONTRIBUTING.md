# Contributing / Engineering Workflow

This is a personal engineering portfolio, but changes follow a production-style workflow so the history remains reviewable.

1. Open an issue that states the problem, evidence and acceptance criteria.
2. Create a focused branch such as `feat/...`, `fix/...`, `docs/...` or `security/...`.
3. Make small, meaningful commits. Do not manufacture history or split commits only to create activity.
4. Add or update tests for behavior changes.
5. Open a pull request that explains what changed, why, validation performed and known limitations.
6. Require CI to pass before merging.
7. Prefer squash merge for a concise main-branch history.

## Evidence rule

Do not claim a cloud deployment, benchmark, reliability result, cost saving, certification or production outcome unless the repository contains sanitized evidence that supports it.

## Secrets

Never commit passwords, API keys, cloud credentials, kubeconfigs, Terraform state or employer/customer material.
