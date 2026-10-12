"""Create a redacted, fail-closed review packet from `terraform show -json`."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 5_000_000
MAX_CHANGES = 1_000
KNOWN_ACTIONS = {"no-op", "create", "read", "update", "delete"}
PRIVILEGE_PATTERNS = (
    "aws_iam_*",
    "aws_kms_*",
    "azurerm_role_*",
    "azuread_*",
    "google_*_iam_*",
    "kubernetes_cluster_role*",
)
NETWORK_TYPES = (
    "aws_security_group*",
    "azurerm_network_security_rule",
    "google_compute_firewall",
)
PUBLIC_CIDRS = {"0.0.0.0/0", "::/0", "*"}


class InvalidPlan(ValueError):
    """Raised for inputs that cannot be safely evaluated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidPlan(message)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise InvalidPlan("non-finite JSON number")


def load_json(path: str | Path) -> Any:
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, "input exceeds 5 MB")
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidPlan("invalid JSON") from error


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _truthy_leaf(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, dict):
        return any(_truthy_leaf(item) for item in value.values())
    if isinstance(value, list):
        return any(_truthy_leaf(item) for item in value)
    return False


def _contains_public_cidr(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip() in PUBLIC_CIDRS
    if isinstance(value, dict):
        return any(_contains_public_cidr(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_public_cidr(item) for item in value)
    return False


def _matches(resource_type: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(resource_type, pattern) for pattern in patterns)


def _finding(code: str, severity: str, address: str, explanation: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "address": address,
        "explanation": explanation,
    }


def _validate_change(item: Any) -> tuple[str, str, list[str], dict[str, Any]]:
    require(isinstance(item, dict), "resource change must be an object")
    address = item.get("address")
    resource_type = item.get("type")
    change = item.get("change")
    require(isinstance(address, str) and 0 < len(address) <= 300, "invalid address")
    require(isinstance(resource_type, str) and 0 < len(resource_type) <= 200, "invalid type")
    require(isinstance(change, dict), "missing change object")
    actions = change.get("actions")
    require(isinstance(actions, list) and 1 <= len(actions) <= 2, "invalid actions")
    require(all(isinstance(action, str) for action in actions), "actions must be strings")
    require(set(actions) <= KNOWN_ACTIONS, "unknown action")
    valid_sequences = {
        ("no-op",), ("create",), ("read",), ("update",), ("delete",),
        ("delete", "create"), ("create", "delete"),
    }
    require(tuple(actions) in valid_sequences, "unsupported action sequence")
    return address, resource_type, actions, change


def evaluate(plan: Any, *, max_changes: int = 200) -> dict[str, Any]:
    """Evaluate Terraform plan JSON without returning planned values."""
    require(isinstance(plan, dict), "plan must be an object")
    format_version = plan.get("format_version")
    terraform_version = plan.get("terraform_version")
    require(isinstance(format_version, str) and format_version.startswith("1."),
            "unsupported Terraform JSON format")
    require(isinstance(terraform_version, str) and terraform_version,
            "missing Terraform version")
    changes = plan.get("resource_changes")
    require(isinstance(changes, list), "resource_changes must be a list")
    require(len(changes) <= MAX_CHANGES, "too many resource changes")
    require(type(max_changes) is int and 1 <= max_changes <= MAX_CHANGES,
            "invalid max_changes")

    findings: list[dict[str, str]] = []
    summary = {name: 0 for name in ("create", "update", "delete", "replace", "read", "no-op")}
    resources: list[dict[str, Any]] = []

    if len(changes) > max_changes:
        findings.append(_finding(
            "CHANGE_LIMIT_EXCEEDED", "high", "plan",
            f"Plan contains {len(changes)} resource changes; reviewed limit is {max_changes}.",
        ))

    for item in changes:
        address, resource_type, actions, change = _validate_change(item)
        action_key = "replace" if len(actions) == 2 else actions[0]
        summary[action_key] += 1
        resource_findings: list[str] = []

        if "delete" in actions:
            code = "RESOURCE_REPLACEMENT" if len(actions) == 2 else "RESOURCE_DELETION"
            findings.append(_finding(
                code, "high", address,
                "Replacement or deletion requires an explicit owner-reviewed migration and rollback plan.",
            ))
            resource_findings.append(code)

        if _matches(resource_type, PRIVILEGE_PATTERNS) and actions not in (["no-op"], ["read"]):
            findings.append(_finding(
                "PRIVILEGE_CHANGE", "high", address,
                "Identity, access, role or encryption-key policy is changing.",
            ))
            resource_findings.append("PRIVILEGE_CHANGE")

        after = change.get("after")
        if _matches(resource_type, NETWORK_TYPES) and after is not None and _contains_public_cidr(after):
            findings.append(_finding(
                "PUBLIC_NETWORK_EXPOSURE", "critical", address,
                "Planned network configuration contains a world-routable CIDR or wildcard.",
            ))
            resource_findings.append("PUBLIC_NETWORK_EXPOSURE")

        if resource_type == "aws_s3_bucket_public_access_block" and isinstance(after, dict):
            controls = (
                "block_public_acls", "block_public_policy",
                "ignore_public_acls", "restrict_public_buckets",
            )
            if any(after.get(control) is not True for control in controls):
                findings.append(_finding(
                    "S3_PUBLIC_GUARD_WEAKENED", "critical", address,
                    "All four S3 public-access-block controls must remain true.",
                ))
                resource_findings.append("S3_PUBLIC_GUARD_WEAKENED")

        if resource_type == "azurerm_kubernetes_cluster" and isinstance(after, dict):
            if after.get("private_cluster_enabled") is not True:
                findings.append(_finding(
                    "AKS_PUBLIC_CONTROL_PLANE", "critical", address,
                    "AKS control plane is not explicitly planned as private.",
                ))
                resource_findings.append("AKS_PUBLIC_CONTROL_PLANE")
            if after.get("local_account_disabled") is not True:
                findings.append(_finding(
                    "AKS_LOCAL_ACCOUNTS_ENABLED", "high", address,
                    "AKS local administrator accounts are not explicitly disabled.",
                ))
                resource_findings.append("AKS_LOCAL_ACCOUNTS_ENABLED")

        sensitive = _truthy_leaf(change.get("before_sensitive")) or _truthy_leaf(
            change.get("after_sensitive")
        )
        resources.append({
            "address": address,
            "type": resource_type,
            "actions": actions,
            "contains_sensitive_markers": sensitive,
            "finding_codes": sorted(resource_findings),
        })

    findings.sort(key=lambda item: (item["severity"], item["code"], item["address"]))
    blocking = any(item["severity"] in {"critical", "high"} for item in findings)
    return {
        "schema": 1,
        "decision": "hold" if blocking else "ready_for_human_review",
        "execution_authorized": False,
        "plan_sha256": canonical_digest(plan),
        "terraform_version": terraform_version,
        "format_version": format_version,
        "change_count": len(changes),
        "summary": summary,
        "findings": findings,
        "resources": resources,
        "redaction": {
            "planned_values_emitted": False,
            "before_after_values_emitted": False,
            "sensitive_values_emitted": False,
        },
        "next_step": "Human review is always required; this tool never runs Terraform.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="Path to sanitized `terraform show -json` output")
    parser.add_argument("--max-changes", type=int, default=200)
    args = parser.parse_args(argv)
    try:
        packet = evaluate(load_json(args.plan), max_changes=args.max_changes)
        print(json.dumps(packet, indent=2, sort_keys=True, allow_nan=False))
        return 0 if packet["decision"] == "ready_for_human_review" else 1
    except (InvalidPlan, OSError, TypeError, ValueError, OverflowError, RecursionError):
        print(json.dumps({
            "schema": 1,
            "decision": "invalid",
            "execution_authorized": False,
            "error": "Input could not be safely evaluated; check the documented contract.",
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
