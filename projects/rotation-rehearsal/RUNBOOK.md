# Rehearsal runbook

This runbook describes a proposed operator workflow. The CLI only analyzes files and never performs these operational changes.

## Before a real migration is separately authorized

1. Inventory every consumer, including scheduled jobs, sidecars, connection pools and recovery processes. Obtain service-owner review. An omitted consumer cannot be detected by this tool.
2. Confirm the provider and application support an overlap period with both versions valid. Single-active-password systems require another design; this planner does not make them safe automatically.
3. Confirm the old version's actual expiry, revocation semantics and rollback behavior. Choose realistic rollout and verification estimates; reserve operator capacity explicitly. Dependencies describe verified migration order.
4. Use opaque aliases in a sanitized manifest. Keep all credential values in the approved secrets manager. Run the planner with the intended start time, review the waves, expiry margin and assumptions. Archive the manifest, command, report and code revision in a restricted location.

## During a separately approved migration

Operators would introduce the new version through their existing approved process, then supervise each planned wave. For each consumer, exercise a request or job that actually uses the new version; readiness alone is insufficient. Record actual timing, version and outcome from trusted collectors. Wait for every member of a wave to pass before proceeding.

If a wave fails or runs late, stop progression and retain the old credential where provider policy permits. Revert affected consumers through reviewed procedures if safe; do not revoke the old credential to force migration. Replan using realistic remaining time and collect fresh evidence. The CLI does not track wave execution or decide whether rollback is safe.

## Interpreting the retirement report

| Check | Investigation on failure |
|---|---|
| `expiry_window` / `current_expiry_margin` | Review expiry with the credential owner; postpone or arrange an authorized new window. Never edit expiry to hide the risk. |
| `plan_binding` | Manifest or start changed, or the evidence came from another rehearsal. Regenerate observations for the reviewed plan. |
| `complete_inventory` | Compare supplied observations against the reviewed consumer list; investigate missing and unexpected consumers. |
| `planned_finish_reached` | Evaluation precedes estimated completion. Wait and verify actual completion. |
| `consumer_on_new_version_healthy_and_fresh` | Check version rollout, functional probe, timestamp, age and health; collect a new verified observation. |

After all checks pass, a human still verifies actual wave completion, inventory completeness, dual-version behavior, evidence provenance and emergency recovery arrangements. Only an independent authorized process may retire the old version. Recheck afterward for authentication errors and hidden consumers. A rehearsal report cannot replace that process.

## Failure, reporting and cleanup

Exit 1 is a modeled hold; retain the JSON report for diagnosis. Exit 2 indicates invalid input; consult the schema and validate locally. Do not print private input into shared CI logs. No output file is written unless the caller redirects stdout, and no resources are provisioned.

Cleanup: remove only generated rehearsal reports you created and the local `__pycache__` directory if desired. Keep committed synthetic samples. There are no cloud resources, credentials or accounts to delete. Real migration records belong in the organization's approved retention system, not in this public repository.
