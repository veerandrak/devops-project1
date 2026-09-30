# ReleaseGuard — evidence before release
An original portfolio implementation of an offline, explainable release gate. It combines service readiness and error-budget signals with recent restore evidence. This is a new lab, not an employer production system or a claim of global novelty.

## Run
Python 3.11+; standard library only. From this directory:
```sh
python -m unittest -v
python releaseguard.py samples/healthy.json --release-id checkout-2026.09.30 --environment staging --replay-at 2026-09-30T10:00:00Z
```
Synthetic replay deliberately exits **1** even when the scenario decision is `pass`: `release_authorized` remains false. In CI, omit `--replay-at`, supply fresh evidence from trusted collectors, and gate deployment on exit status **0**. Exit 1 means held; exit 2 means unreadable/invalid JSON or command-input error. Standard argparse usage errors also exit 2.

## Fixed lab policy
Telemetry age 0–300 seconds; 100+ requests over 60–300 seconds; error ratio <=1%; all desired replicas ready. Restore age 0–24 hours; checksum verified; duration <=900 seconds. Evidence must bind the release and environment; restore must identify backup, digest and environment. Policy is intentionally code-reviewed, not relaxed by an untrusted evidence document. Zero traffic is insufficient evidence.

JSON output lists each check, its result and explanation. Missing fields, wrong types, future or naive timestamps, invalid counts, duplicate JSON keys, NaN and infinity fail closed. See samples for healthy, error regression, stale telemetry and failed restore. All sample identifiers and results are synthetic.

## Trust boundary and operations
This evaluates supplied evidence, not its authenticity. Collectors must calculate the actual restored artifact digest, observe live service metrics and emit the schema demonstrated in samples. Store evidence and gate JSON as CI artifacts. Restrict who can edit the pipeline and evidence; do not allow callers to add replay flags. A digest-shaped string alone is not proof of a restore. There is no signature verification, cloud API integration, deployment or automatic rollback.

On hold, investigate failing checks and collect new evidence. Do not edit timestamps or lower thresholds to make a release pass. A human can make an incident decision outside this tool's scope; keep that decision auditable. Future work: signed collector attestations and per-service reviewed policy bundles.
