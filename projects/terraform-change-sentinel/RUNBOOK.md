# Change-review runbook

This runbook describes a proposed review workflow. Change Sentinel creates evidence for a human; it never authorizes or executes infrastructure changes.

## Prepare

1. Use an approved, isolated runner with short-lived cloud credentials and an encrypted/locked Terraform backend. Confirm the workspace and account before planning.
2. Refresh the branch and dependency lock files, then run formatting, validation and the project's normal tests/security checks.
3. Create a saved plan. Treat both the binary plan and `terraform show -json` output as secrets because they may contain sensitive values in cleartext.
4. Run Change Sentinel locally and retain only the redacted packet under the organization's approved access and retention policy. Verify the packet SHA-256 against the exact reviewed JSON immediately before the approval record is completed.

## Review

The reviewer checks scope, account/workspace, ownership, maintenance window, dependencies, backup/restore readiness, rollback plan and monitoring. They compare the resource list and summary to the change request and investigate every finding.

| Finding | Required investigation |
|---|---|
| `RESOURCE_DELETION` / `RESOURCE_REPLACEMENT` | Confirm data classification, backup and tested restore, migration sequencing, downtime, dependency impact and rollback limitations. |
| `PRIVILEGE_CHANGE` | Review the complete policy diff for least privilege, trust relationships, wildcard actions/resources, escalation paths and separation of duties. |
| `PUBLIC_NETWORK_EXPOSURE` | Confirm intended source ranges and ports. Replace world access with approved private paths or narrowly scoped sources. |
| `S3_PUBLIC_GUARD_WEAKENED` | Keep all four controls enabled unless a separately governed public-data design exists. Check bucket policy and organization controls too. |
| `AKS_PUBLIC_CONTROL_PLANE` / `AKS_LOCAL_ACCOUNTS_ENABLED` | Require private administration paths, Entra/RBAC access and a tested break-glass process that does not normalize local accounts. |
| `CHANGE_LIMIT_EXCEEDED` | Split the change or arrange an expanded review with clear dependency groups and rollback checkpoints. |

A hold is not an error to suppress. Revise the Terraform or document the risk in the independent approval system. This CLI intentionally has no exemption file or `--force` option.

## Apply and observe—outside this tool

After separate authorization, verify that the saved binary plan still matches the reviewed workflow and has not been regenerated silently. Apply through the approved pipeline. Monitor provider errors, health signals, authentication failures, exposure changes and resource replacement progress. Stop or roll back according to the reviewed plan; do not improvise destructive recovery.

The analyzer does not validate the binary plan, state lock, identity, signature, approval, apply result or post-deployment health. Those remain pipeline and operator responsibilities.

## Cleanup

Delete the local binary plan and private JSON through the organization's approved secure process when retention no longer requires them. Restrict and expire review artifacts because resource addresses reveal architecture. Never publish real plan JSON, state, credentials, kubeconfigs, account IDs, private hostnames or employer/customer data in this portfolio. This lab creates no cloud resources and has nothing to destroy.
