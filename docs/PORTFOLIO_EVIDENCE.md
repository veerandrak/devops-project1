# Portfolio Evidence Matrix

This file gives recruiters and reviewers a fast way to distinguish **implemented**, **tested**, **locally runnable**, and **cloud deployed** work.

| Project | Implemented | Automated tests | Local execution path | Cloud deployment evidence | Key limitation |
|---|:---:|:---:|:---:|:---:|---|
| AI DevOps Incident Agent | ✅ | ✅ | ✅ | — | Deterministic baseline; no LLM/RAG/tools yet |
| ReleaseGuard | ✅ | ✅ | ✅ | — | Evidence authenticity comes from trusted collectors |
| Rotation Rehearsal | ✅ | ✅ | ✅ | — | Offline planner; no live secrets-provider adapter |
| Kubernetes Reliability Lab | ✅ | ✅ | ✅ documented | ❌ | Docker/Kubernetes/Jenkins execution evidence not yet published |
| AWS Encrypted Backup Lab | ✅ | ✅ | ✅ documented | ❌ | Real S3/KMS plan/apply/restore evidence not yet published |
| Azure AKS Platform Lab | ✅ | validation-oriented | ✅ documented | ❌ | Provider/deployment verification remains incomplete |

## Evidence policy

- ✅ means repository evidence exists for that category.
- ❌ means the portfolio explicitly does **not** claim that evidence yet.
- A design document, Terraform file or pipeline definition does not by itself prove successful deployment.
- Future cloud screenshots/logs must be sanitized before publication: remove account IDs where appropriate, tokens, tenant-sensitive information, internal hostnames, kubeconfigs and any customer/employer data.

## Next evidence milestones

1. Run and capture a clean GitHub Actions CI result.
2. Run the Kubernetes lab on a disposable local cluster and publish sanitized rollout/rollback evidence.
3. Run the AWS backup lab in a disposable account/sandbox and publish a sanitized plan, backup receipt and verified restore.
4. Complete an AKS `terraform validate`/plan against an authorized sandbox before claiming deployability.
5. Add measurable retrieval evaluation when the Incident Agent gains RAG.
