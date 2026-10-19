# DrainScope operational runbook

## Purpose

Use DrainScope as an offline **pre-review**, not as drain authorization. The operator remains responsible for a fresh cluster preflight and the approved maintenance procedure.

## 1. Collect minimal evidence

From an authorized, read-only context, build schema `1.0` using only the fields in `samples/ready.json`. Calculate pod eligibility from selectors, affinity and taints/tolerations in the collector. Record current requests and free allocatable capacity after system reservations. Never export Secret data, environment values, ConfigMap contents, tokens or kubeconfig material.

Keep the snapshot in a restricted temporary directory. Generate it immediately before review; the default maximum age is five minutes.

## 2. Evaluate

```bash
python drainscope.py snapshot.private.json > review-packet.json
status=$?
```

- `0`: evidence is ready for human review, not permission to drain.
- `1`: one or more maintenance blockers were detected.
- `2`: evidence or command input is invalid; recollect it.

Record the snapshot fingerprint, packet, collector version and reviewer decision in the authorized change record. Do not publish cluster identifiers.

## 3. Handle a hold

| Finding | Operator response |
|---|---|
| `SNAPSHOT_STALE` | Recollect; never edit the timestamp. |
| `PDB_BUDGET_EXCEEDED` | Restore workload health or schedule separate evictions; do not weaken the PDB just to pass. |
| `CONTROLLER_DEGRADED` | Resolve missing replicas before voluntary disruption. |
| `LOCAL_STORAGE_RISK` | Verify data classification and an approved preservation/recovery path. |
| `NO_ELIGIBLE_NODE` / `INSUFFICIENT_REPLACEMENT_CAPACITY` | Add approved capacity or correct placement constraints, then recollect. |
| `TOPOLOGY_CONCENTRATION` | Restore zone diversity or document an explicit risk decision outside this tool. |
| `UNMANAGED_POD` / `STATIC_POD` / `CRITICAL_POD` | Identify ownership and use the workload-specific maintenance procedure. |

Do not modify the JSON, disable checks or inflate capacity to create a passing packet.

## 4. Live preflight and maintenance

After an authorized reviewer accepts the packet, follow the cluster's own maintenance runbook. Recheck node readiness, PDBs, replica health, pending pods, events, autoscaler status and rollback conditions. Use Kubernetes dry-run/eviction facilities where supported. DrainScope deliberately does not provide an execution command because flags and safety constraints are environment-specific.

## 5. Observe and rollback

Watch rollout health, error rate, latency, saturation, pending pods and zone distribution during the change. Stop under the approved rollback criteria. A DrainScope pass is not evidence that the live drain succeeded.

## 6. Cleanup

Delete the private snapshot and any packet containing internal names according to the change-record retention policy. Never commit generated evidence. Confirm temporary files are absent with `git status --ignored` before pushing code.
