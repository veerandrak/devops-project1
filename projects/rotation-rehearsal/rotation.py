"""Offline credential rotation planning; never reads or rotates credentials."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_BYTES = 1_000_000
FRESH_SECONDS = 300
SAFETY_SECONDS = 600


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names.split()), "invalid object fields")


def identifier(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value),
            "invalid metadata identifier")
    return value


def integer(value, low=1, high=86400):
    require(type(value) is int and low <= value <= high, "invalid integer range")
    return value


def stamp(value):
    require(type(value) is str, "timestamp must be text")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise Invalid("invalid timestamp") from None
    require(result.tzinfo is not None, "timestamp requires timezone")
    return result.astimezone(timezone.utc)


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise Invalid("nonfinite JSON number")

    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "input too large")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def plan(manifest, start):
    """Build deterministic barrier waves; dependencies mean rollout order."""
    fields(manifest, "schema rotation_id environment credential_id old_version new_version expires_at teams consumers")
    require(type(manifest["schema"]) is int and manifest["schema"] == 1, "unsupported schema")
    for key in ("rotation_id", "environment", "credential_id", "old_version", "new_version"):
        identifier(manifest[key])
    require(manifest["old_version"] != manifest["new_version"], "versions must differ")
    expiry = stamp(manifest["expires_at"])
    teams = manifest["teams"]
    require(type(teams) is dict and 0 < len(teams) <= 100, "teams required")
    for team, capacity in teams.items():
        identifier(team)
        integer(capacity, high=100)
    consumers = manifest["consumers"]
    require(type(consumers) is list and 0 < len(consumers) <= 100, "consumers required")
    by_id = {}
    for item in consumers:
        fields(item, "id team depends_on rollout_seconds verify_seconds")
        name = identifier(item["id"])
        require(name not in by_id, "duplicate consumer")
        require(type(item["team"]) is str and item["team"] in teams, "unknown team")
        for key in ("rollout_seconds", "verify_seconds"):
            integer(item[key])
        deps = item["depends_on"]
        require(type(deps) is list and len(deps) <= 100, "invalid dependencies")
        for dep in deps:
            identifier(dep)
        require(len(set(deps)) == len(deps), "duplicate dependency")
        by_id[name] = item
    for name, item in by_id.items():
        require(all(dep in by_id and dep != name for dep in item["depends_on"]),
                "unknown or self dependency")
    done, waves, offset = set(), [], 0
    while len(done) < len(by_id):
        ready = sorted(name for name, item in by_id.items()
                       if name not in done and set(item["depends_on"]) <= done)
        require(bool(ready), "dependency cycle")
        used, chosen = {}, []
        for name in ready:
            team = by_id[name]["team"]
            if used.get(team, 0) < teams[team]:
                chosen.append(name)
                used[team] = used.get(team, 0) + 1
        duration = max(by_id[name]["rollout_seconds"] + by_id[name]["verify_seconds"]
                       for name in chosen)
        waves.append({"number": len(waves) + 1, "consumers": chosen,
                      "start_offset_seconds": offset, "duration_seconds": duration})
        offset += duration
        done.update(chosen)
    finish = start + timedelta(seconds=offset)
    margin = (expiry - finish).total_seconds()
    safe = margin >= SAFETY_SECONDS
    return {"schema": 1, "rotation_id": manifest["rotation_id"],
            "environment": manifest["environment"], "new_version": manifest["new_version"],
            "plan_id": digest({"manifest": manifest, "start": iso(start)}),
            "start_at": iso(start), "finish_at": iso(finish), "waves": waves,
            "estimated_seconds": offset, "expiry_margin_seconds": margin,
            "decision": "ready_for_review" if safe else "hold",
            "reasons": [] if safe else ["expiry window lacks 600-second safety margin"],
            "execution_authorized": False}


def retirement_report(manifest, start, evidence, now):
    """Check synthetic observations; never authorize actual revocation."""
    result = plan(manifest, start)
    fields(evidence, "plan_id observations")
    require(type(evidence["plan_id"]) is str, "invalid plan id")
    observations = evidence["observations"]
    require(type(observations) is list and len(observations) <= 100, "invalid observations")
    seen = {}
    for obs in observations:
        fields(obs, "consumer version healthy observed_at")
        name = identifier(obs["consumer"])
        require(name not in seen, "duplicate observation")
        identifier(obs["version"])
        require(type(obs["healthy"]) is bool, "health must be boolean")
        stamp(obs["observed_at"])
        seen[name] = obs
    expected = {item["id"] for item in manifest["consumers"]}
    checks = [{"check": "expiry_window", "ok": result["decision"] != "hold"},
              {"check": "plan_binding", "ok": evidence["plan_id"] == result["plan_id"]},
              {"check": "complete_inventory", "ok": set(seen) == expected},
              {"check": "planned_finish_reached", "ok": now >= stamp(result["finish_at"])}]
    expiry_ok = (stamp(manifest["expires_at"]) - now).total_seconds() >= SAFETY_SECONDS
    checks.append({"check": "current_expiry_margin", "ok": expiry_ok})
    for name in sorted(expected):
        obs = seen.get(name)
        ok = False
        if obs:
            observed = stamp(obs["observed_at"])
            ok = (obs["healthy"] and obs["version"] == manifest["new_version"]
                  and stamp(result["finish_at"]) <= observed <= now
                  and (now - observed).total_seconds() <= FRESH_SECONDS)
        checks.append({"check": "consumer_on_new_version_healthy_and_fresh", "consumer": name, "ok": ok})
    return {"decision": "ready_for_review" if all(c["ok"] for c in checks) else "hold",
            "plan_id": result["plan_id"], "checks": checks,
            "execution_authorized": False,
            "next_step": "human review; this tool never rotates or revokes credentials"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--start-at", required=True, help="explicit rehearsal start timestamp")
    parser.add_argument("--evidence", help="metadata-only synthetic observations")
    parser.add_argument("--check-at", help="explicit rehearsal evidence evaluation timestamp")
    args = parser.parse_args(argv)
    try:
        require(bool(args.evidence) == bool(args.check_at), "evidence and check-at must be paired")
        manifest, start = load(args.manifest), stamp(args.start_at)
        if args.evidence:
            result = retirement_report(manifest, start, load(args.evidence), stamp(args.check_at))
        else:
            result = plan(manifest, start)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["decision"] == "ready_for_review" else 1
    except (Invalid, OSError, ValueError, TypeError, OverflowError, RecursionError):
        # Never echo input, file contents, paths, or exception details to logs.
        print(json.dumps({"decision": "invalid", "execution_authorized": False,
                          "error": "Invalid input; check the documented metadata schema."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
