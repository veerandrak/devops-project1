#!/usr/bin/env python3
"""Offline Kubernetes node-drain readiness analysis.

DrainScope consumes a sanitized inventory snapshot. It never contacts a cluster or
authorizes a drain; its output is evidence for a human maintenance review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_PODS = 500
MAX_NODES = 200
DEFAULT_MAX_AGE_SECONDS = 300
TERMINAL_PHASES = {"Succeeded", "Failed"}


class InputError(ValueError):
    """Raised when evidence is malformed or insufficient."""


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise InputError(f"{field} must be an RFC3339 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise InputError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InputError(f"{field} must be an integer >= {minimum}")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} must be a non-empty string")
    return value


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise InputError(f"{field} must be a boolean")
    return value


def _resource_pair(value: Any, field: str) -> tuple[int, int]:
    if not isinstance(value, dict):
        raise InputError(f"{field} must be an object")
    return (
        _integer(value.get("cpu_millicores"), f"{field}.cpu_millicores"),
        _integer(value.get("memory_mib"), f"{field}.memory_mib"),
    )


def _finding(code: str, subject: str, explanation: str) -> dict[str, str]:
    return {"code": code, "subject": subject, "explanation": explanation}


@dataclass
class Candidate:
    subject: str
    cpu: int
    memory: int
    eligible_nodes: tuple[str, ...]


def load_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError("unable to read snapshot") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise InputError("snapshot exceeds 2 MiB limit")
    try:
        data = json.loads(
            raw,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                InputError(f"invalid JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError("snapshot must be valid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise InputError("snapshot root must be an object")
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return data, hashlib.sha256(canonical).hexdigest()


def analyze(
    snapshot: dict[str, Any],
    *,
    observed_at: datetime,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    schema = snapshot.get("schema_version")
    if schema != "1.0":
        raise InputError("schema_version must be 1.0")
    generated_at = _parse_time(snapshot.get("generated_at"), "generated_at")
    age = int((observed_at - generated_at).total_seconds())
    if age < 0:
        raise InputError("generated_at cannot be in the future")

    target = snapshot.get("target_node")
    if not isinstance(target, dict):
        raise InputError("target_node must be an object")
    target_name = _string(target.get("name"), "target_node.name")
    target_zone = _string(target.get("zone"), "target_node.zone")

    nodes = snapshot.get("replacement_nodes")
    pods = snapshot.get("pods")
    if not isinstance(nodes, list) or not isinstance(pods, list):
        raise InputError("replacement_nodes and pods must be arrays")
    if len(nodes) > MAX_NODES or len(pods) > MAX_PODS:
        raise InputError("snapshot exceeds node or pod count limit")

    findings: list[dict[str, str]] = []
    notes: list[dict[str, str]] = []
    if age > max_age_seconds:
        findings.append(
            _finding("SNAPSHOT_STALE", "snapshot", f"evidence age {age}s exceeds {max_age_seconds}s")
        )

    capacities: dict[str, list[int]] = {}
    node_zones: dict[str, str] = {}
    for index, node in enumerate(nodes):
        prefix = f"replacement_nodes[{index}]"
        if not isinstance(node, dict):
            raise InputError(f"{prefix} must be an object")
        name = _string(node.get("name"), f"{prefix}.name")
        if name == target_name or name in capacities:
            raise InputError("replacement node names must be unique and exclude target")
        ready = _bool(node.get("ready"), f"{prefix}.ready")
        schedulable = _bool(node.get("schedulable"), f"{prefix}.schedulable")
        zone = _string(node.get("zone"), f"{prefix}.zone")
        cpu, memory = _resource_pair(node.get("free"), f"{prefix}.free")
        node_zones[name] = zone
        if ready and schedulable:
            capacities[name] = [cpu, memory]

    pdb_counts: dict[str, int] = {}
    pdb_allowed: dict[str, int] = {}
    candidates: list[Candidate] = []
    seen_pods: set[str] = set()

    for index, pod in enumerate(pods):
        prefix = f"pods[{index}]"
        if not isinstance(pod, dict):
            raise InputError(f"{prefix} must be an object")
        namespace = _string(pod.get("namespace"), f"{prefix}.namespace")
        name = _string(pod.get("name"), f"{prefix}.name")
        subject = f"{namespace}/{name}"
        if subject in seen_pods:
            raise InputError(f"duplicate pod identity: {subject}")
        seen_pods.add(subject)
        phase = _string(pod.get("phase"), f"{prefix}.phase")
        if phase in TERMINAL_PHASES:
            notes.append(_finding("TERMINAL_POD_IGNORED", subject, f"phase is {phase}"))
            continue

        owner = pod.get("owner")
        if owner is None:
            findings.append(_finding("UNMANAGED_POD", subject, "no recreating controller is recorded"))
            owner_kind = ""
        elif isinstance(owner, dict):
            owner_kind = _string(owner.get("kind"), f"{prefix}.owner.kind")
            _string(owner.get("name"), f"{prefix}.owner.name")
        else:
            raise InputError(f"{prefix}.owner must be an object or null")

        if owner_kind == "DaemonSet":
            notes.append(_finding("DAEMONSET_IGNORED", subject, "kubectl drain normally ignores DaemonSet pods"))
            continue
        if owner_kind in {"Node", "StaticPod"}:
            findings.append(_finding("STATIC_POD", subject, "mirror/static pod is not safely evictable"))
            continue

        if _bool(pod.get("critical"), f"{prefix}.critical"):
            findings.append(_finding("CRITICAL_POD", subject, "critical workload requires explicit operator review"))

        controller = pod.get("controller")
        if controller is not None:
            if not isinstance(controller, dict):
                raise InputError(f"{prefix}.controller must be an object or null")
            desired = _integer(controller.get("desired_replicas"), f"{prefix}.controller.desired_replicas", 1)
            ready = _integer(controller.get("ready_replicas"), f"{prefix}.controller.ready_replicas")
            if ready < desired:
                findings.append(
                    _finding("CONTROLLER_DEGRADED", subject, f"controller has {ready}/{desired} ready replicas")
                )

        storage = pod.get("local_storage", [])
        if not isinstance(storage, list):
            raise InputError(f"{prefix}.local_storage must be an array")
        for storage_index, volume in enumerate(storage):
            if not isinstance(volume, dict):
                raise InputError(f"{prefix}.local_storage[{storage_index}] must be an object")
            kind = _string(volume.get("kind"), f"{prefix}.local_storage[{storage_index}].kind")
            limit = volume.get("size_limit_mib")
            if limit is not None:
                _integer(limit, f"{prefix}.local_storage[{storage_index}].size_limit_mib", 1)
            if kind in {"hostPath", "local"} or (kind == "emptyDir" and limit is None):
                findings.append(
                    _finding("LOCAL_STORAGE_RISK", subject, f"{kind} data may be lost or has no recorded bound")
                )

        pdb = pod.get("pdb")
        if pdb is not None:
            if not isinstance(pdb, dict):
                raise InputError(f"{prefix}.pdb must be an object or null")
            pdb_name = _string(pdb.get("name"), f"{prefix}.pdb.name")
            allowed = _integer(pdb.get("disruptions_allowed"), f"{prefix}.pdb.disruptions_allowed")
            pdb_counts[pdb_name] = pdb_counts.get(pdb_name, 0) + 1
            if pdb_name in pdb_allowed and pdb_allowed[pdb_name] != allowed:
                raise InputError(f"inconsistent disruption budget for {pdb_name}")
            pdb_allowed[pdb_name] = allowed

        cpu, memory = _resource_pair(pod.get("requests"), f"{prefix}.requests")
        eligible = pod.get("eligible_nodes")
        if not isinstance(eligible, list) or not all(isinstance(item, str) and item for item in eligible):
            raise InputError(f"{prefix}.eligible_nodes must be an array of node names")
        eligible_ready = tuple(sorted({node for node in eligible if node in capacities}))
        if not eligible_ready:
            findings.append(_finding("NO_ELIGIBLE_NODE", subject, "no ready schedulable replacement node is eligible"))
        else:
            candidates.append(Candidate(subject, cpu, memory, eligible_ready))

        peer_zones = pod.get("peer_zones", [])
        if not isinstance(peer_zones, list) or not all(isinstance(zone, str) and zone for zone in peer_zones):
            raise InputError(f"{prefix}.peer_zones must be an array of zone names")
        if controller is not None and _integer(controller.get("desired_replicas"), f"{prefix}.controller.desired_replicas", 1) > 1:
            remaining_zones = set(peer_zones)
            remaining_zones.discard(target_zone)
            possible_zones = {node_zones[node] for node in eligible_ready}
            if len(remaining_zones | possible_zones) < 2:
                findings.append(
                    _finding("TOPOLOGY_CONCENTRATION", subject, "replacement cannot preserve a two-zone replica footprint")
                )

    for pdb_name in sorted(pdb_counts):
        if pdb_counts[pdb_name] > pdb_allowed[pdb_name]:
            findings.append(
                _finding(
                    "PDB_BUDGET_EXCEEDED",
                    f"pdb/{pdb_name}",
                    f"drain evicts {pdb_counts[pdb_name]} matched pods but only {pdb_allowed[pdb_name]} disruptions are allowed",
                )
            )

    # Deterministic constrained first-fit-decreasing simulation. This is a
    # conservative scheduling approximation, not a kube-scheduler replacement.
    for candidate in sorted(candidates, key=lambda item: (-item.memory, -item.cpu, item.subject)):
        choices = [
            name
            for name in candidate.eligible_nodes
            if capacities[name][0] >= candidate.cpu and capacities[name][1] >= candidate.memory
        ]
        if not choices:
            findings.append(
                _finding("INSUFFICIENT_REPLACEMENT_CAPACITY", candidate.subject, "no eligible node has remaining requested CPU and memory")
            )
            continue
        selected = max(choices, key=lambda name: (capacities[name][1] - candidate.memory, capacities[name][0] - candidate.cpu, name))
        capacities[selected][0] -= candidate.cpu
        capacities[selected][1] -= candidate.memory

    findings.sort(key=lambda item: (item["code"], item["subject"]))
    notes.sort(key=lambda item: (item["code"], item["subject"]))
    return {
        "decision": "hold" if findings else "ready_for_human_review",
        "drain_authorized": False,
        "target_node": target_name,
        "snapshot_age_seconds": age,
        "eviction_candidates": len(candidates),
        "findings": findings,
        "notes": notes,
        "limitations": [
            "offline approximation; it does not call the Kubernetes scheduler or eviction API",
            "human approval and a fresh live preflight remain required before any drain",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate sanitized Kubernetes node-drain evidence")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--at", help="RFC3339 evaluation time for reproducible offline replay")
    parser.add_argument("--max-age-seconds", type=int, default=DEFAULT_MAX_AGE_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_age_seconds < 1:
        print(json.dumps({"error": "max age must be positive"}, sort_keys=True))
        return 2
    try:
        snapshot, fingerprint = load_snapshot(args.snapshot)
        observed_at = _parse_time(args.at, "--at") if args.at else datetime.now(timezone.utc)
        result = analyze(snapshot, observed_at=observed_at, max_age_seconds=args.max_age_seconds)
        result["snapshot_fingerprint_sha256"] = fingerprint
        if args.at:
            result["replay_mode"] = True
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["decision"] == "ready_for_human_review" else 1
    except InputError as exc:
        print(json.dumps({"decision": "invalid", "drain_authorized": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
