# Sai Veerandra Kurakula | Cloud & DevOps Engineering

Building secure infrastructure, repeatable delivery and operational evidence with **AWS, Azure, Kubernetes, Terraform, Jenkins and Python**.

Based in Visakhapatnam, India · Open to fully remote Cloud, DevOps, SRE and Platform opportunities.

My background includes 6+ years across build/release engineering and cloud operations, with AWS/EKS/ECS and Azure/AKS, Linux, Python/Bash, infrastructure as code, CI/CD, observability and secrets-management integrations. These newly authored labs demonstrate those areas; they are not employer code, historical production results or certification claims.

## Explore the portfolio

| Project | What to review | Local evidence |
|---|---|---|
| [Kubernetes SRE lab](projects/kubernetes-sre-lab) | Health/metrics API, hardened deployment, disruption budget, network policy, Prometheus alerts and Jenkins pipeline | 4 Python integration tests |
| [AWS encrypted backup lab](projects/aws-encrypted-backup-lab) | S3/KMS/IAM Terraform; version-specific backup and integrity-checked restore CLI | 4 Python unit tests |
| [Azure AKS platform lab](projects/azure-aks-platform-lab) | Private API/DNS, Entra RBAC, managed/workload identity, overlay networking and Azure DevOps validation pipeline | Terraform fmt + HCL/YAML parsing; see validation notes |
| [Rotation Rehearsal](projects/rotation-rehearsal) | Dependency-aware credential migration waves, team capacity, expiry and retirement evidence checks | 15 Python tests; synthetic healthy/old-version scenarios |
| [ReleaseGuard](projects/releaseguard) | Explainable release pass/hold decisions combining telemetry and restore evidence | 14 Python tests; synthetic pass/hold scenarios |

**Start with ReleaseGuard** for the engineering decisions: fail-closed input handling, explicit trust boundaries, release/environment binding and replay that cannot authorize deployment. It is an original implementation for this portfolio, without a claim that the concept is globally unique.

## Reproduce local tests

After cloning this repository, use Python 3.12:
```sh
(cd projects/kubernetes-sre-lab && python -m unittest -v)
# AWS tests require the dependencies listed in that project's requirements.txt
(cd projects/aws-encrypted-backup-lab && python -m unittest -v)
(cd projects/releaseguard && python -m unittest -v)
(cd projects/rotation-rehearsal && python -m unittest -v)
```
Each project contains its own setup, design decisions and operational limitations. Azure's pipeline is validation-only and requires a configured agent; it does not deploy anything.

## Validation boundaries

The original four labs' 22 Python tests passed during their September 30 authoring validation. Rotation Rehearsal's 15 tests passed locally on October 5; its CLI samples were also exercised. The original tests were not rerun for this isolated addition. Rotation Rehearsal is offline and has no live secrets-provider integration. AKS Terraform formatting, HCL/YAML parsing and provider initialization passed; provider-schema validation was blocked by a local plugin handshake failure. Terraform provider validation and cloud plans/provisioning, Docker/Compose, Kubernetes deployment, Jenkins and Azure DevOps execution have not been demonstrated. Syntax parsing is not proof of deployability. No cloud resources were created and no production reliability, savings or compliance outcomes are claimed.

The existing [HTML page](index.html) is preserved. This repository is the portfolio landing page; the projects are intentionally grouped for convenient review.
