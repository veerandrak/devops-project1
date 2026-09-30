"""Offline release gate. Evidence is supplied by trusted collectors, not attested here."""
import argparse
import json
import math
import sys
from datetime import datetime, timezone

class InvalidEvidence(ValueError):
    pass

def timestamp(value):
    if not isinstance(value, str):
        raise InvalidEvidence('timestamp must be an ISO-8601 string')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise InvalidEvidence('invalid timestamp') from exc
    if parsed.tzinfo is None:
        raise InvalidEvidence('timestamp requires timezone')
    return parsed.astimezone(timezone.utc)

def number(obj, key, minimum=0, integer=False):
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidEvidence(f'{key} must be numeric')
    if not math.isfinite(value) or value < minimum or (integer and not isinstance(value, int)):
        raise InvalidEvidence(f'{key} outside allowed range/type')
    return value

def evaluate(evidence, release_id, environment, now=None):
    now = now or datetime.now(timezone.utc)
    result = {'schema_version': 1, 'decision': 'hold', 'release_id': release_id,
              'environment': environment, 'evaluated_at': now.isoformat(), 'checks': []}
    def check(name, passed, detail):
        result['checks'].append({'name': name, 'passed': bool(passed), 'detail': detail})
    try:
        if not isinstance(evidence, dict) or type(evidence.get('schema_version')) is not int or evidence['schema_version'] != 1:
            raise InvalidEvidence('schema_version must be integer 1')
        for key in ('release_id', 'environment'):
            if not isinstance(evidence.get(key), str) or not evidence[key].strip():
                raise InvalidEvidence(f'{key} is required')
        check('release_binding', evidence['release_id'] == release_id, 'Evidence must match requested release')
        check('environment_binding', evidence['environment'] == environment, 'Evidence must match requested environment')
        observed = timestamp(evidence.get('observed_at'))
        age = (now-observed).total_seconds()
        check('telemetry_freshness', 0 <= age <= 300, f'Age {age:g}s; permitted 0..300s')
        service = evidence.get('service')
        restore = evidence.get('restore')
        if not isinstance(service, dict) or not isinstance(restore, dict):
            raise InvalidEvidence('service and restore objects required')
        ready = number(service, 'ready_replicas', integer=True)
        desired = number(service, 'desired_replicas', minimum=1, integer=True)
        requests = number(service, 'total_requests', integer=True)
        errors = number(service, 'error_requests', integer=True)
        window = number(service, 'window_seconds', minimum=1, integer=True)
        if errors > requests or ready > desired:
            raise InvalidEvidence('inconsistent request/replica counts')
        check('capacity', ready == desired, f'{ready}/{desired} replicas ready')
        check('sample_size', requests >= 100, f'{requests} requests; minimum 100')
        check('observation_window', 60 <= window <= 300, f'{window}s; permitted 60..300s')
        rate = errors/requests if requests else None
        check('error_rate', rate is not None and rate <= 0.01, f'Error ratio {rate}; maximum 0.01')
        completed = timestamp(restore.get('completed_at'))
        restore_age = (now-completed).total_seconds()
        check('restore_freshness', 0 <= restore_age <= 86400, f'Age {restore_age:g}s; permitted 0..86400s')
        if type(restore.get('checksum_verified')) is not bool:
            raise InvalidEvidence('checksum_verified must be boolean')
        for key in ('backup_id', 'artifact_sha256'):
            if not isinstance(restore.get(key), str) or not restore[key].strip():
                raise InvalidEvidence(f'{key} required')
        digest = restore['artifact_sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise InvalidEvidence('artifact_sha256 must be lowercase SHA-256 hex')
        duration = number(restore, 'duration_seconds', minimum=0.001)
        check('restore_integrity', restore['checksum_verified'], 'Collector reports checksum verification')
        check('restore_time', duration <= 900, f'{duration:g}s; recovery budget 900s')
        check('restore_environment', restore.get('environment') == environment, 'Restore must target requested environment')
    except (InvalidEvidence, OverflowError) as exc:
        check('valid_input', False, str(exc))
    if result['checks'] and all(c['passed'] for c in result['checks']):
        result['decision'] = 'pass'
    return result

def reject_constant(value):
    raise ValueError(f'Non-JSON numeric constant: {value}')

def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'Duplicate JSON key: {key}')
        obj[key] = value
    return obj

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence')
    parser.add_argument('--release-id', required=True)
    parser.add_argument('--environment', required=True)
    parser.add_argument('--replay-at', help='Offline synthetic replay only; omit in real release gates')
    args = parser.parse_args(argv)
    try:
        now = timestamp(args.replay_at) if args.replay_at else None
        with open(args.evidence, encoding='utf-8') as stream:
            evidence = json.load(stream, parse_constant=reject_constant, object_pairs_hook=unique_object)
        result = evaluate(evidence, args.release_id, args.environment, now)
        result['mode'] = 'replay' if args.replay_at else 'live'
        # Replay never authorizes a release, even when a scenario passes.
        result['release_authorized'] = result['decision'] == 'pass' and not args.replay_at
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['release_authorized'] else 1
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({'decision': 'hold', 'release_authorized': False,
                          'checks': [{'name': 'read_input', 'passed': False, 'detail': str(exc)}]}))
        return 2

if __name__ == '__main__':
    sys.exit(main())
