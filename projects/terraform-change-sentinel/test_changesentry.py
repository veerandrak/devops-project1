import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from changesentry import InvalidPlan, evaluate, load_json, main

ROOT = Path(__file__).parent


def base_change(resource_type="aws_cloudwatch_log_group", actions=None, after=None):
    return {
        "address": f"{resource_type}.demo",
        "type": resource_type,
        "change": {
            "actions": ["update"] if actions is None else actions,
            "before": {},
            "after": {} if after is None else after,
            "before_sensitive": {},
            "after_sensitive": {},
        },
    }


def plan(*changes):
    return {
        "format_version": "1.2",
        "terraform_version": "1.9.8",
        "resource_changes": list(changes),
    }


class ChangeSentryTests(unittest.TestCase):
    def codes(self, packet):
        return {item["code"] for item in packet["findings"]}

    def test_safe_plan_is_reviewable_and_redacted(self):
        packet = evaluate(load_json(ROOT / "samples/safe-plan.json"))
        self.assertEqual(packet["decision"], "ready_for_human_review")
        self.assertFalse(packet["execution_authorized"])
        self.assertEqual(packet["summary"]["create"], 1)
        encoded = json.dumps(packet)
        self.assertNotIn("retention_in_days", encoded)
        self.assertNotIn('"before":', encoded)
        self.assertNotIn('"after":', encoded)
        self.assertFalse(packet["redaction"]["before_after_values_emitted"])

    def test_risky_sample_holds_with_three_categories(self):
        packet = evaluate(load_json(ROOT / "samples/risky-plan.json"))
        self.assertEqual(packet["decision"], "hold")
        self.assertEqual(packet["summary"]["replace"], 1)
        self.assertTrue({"PUBLIC_NETWORK_EXPOSURE", "PRIVILEGE_CHANGE", "RESOURCE_REPLACEMENT"} <= self.codes(packet))
        self.assertTrue(packet["resources"][1]["contains_sensitive_markers"])
        self.assertNotIn("synthetic-new-policy", json.dumps(packet))

    def test_deletion_and_both_replacement_orders_hold(self):
        cases = (["delete"], ["delete", "create"], ["create", "delete"])
        for actions in cases:
            with self.subTest(actions=actions):
                packet = evaluate(plan(base_change(actions=actions)))
                self.assertEqual(packet["decision"], "hold")

    def test_privilege_patterns_hold(self):
        for resource_type in (
            "aws_iam_policy", "aws_kms_key", "azurerm_role_assignment",
            "azuread_group", "google_project_iam_member", "kubernetes_cluster_role_binding",
        ):
            with self.subTest(resource_type=resource_type):
                self.assertIn("PRIVILEGE_CHANGE", self.codes(evaluate(plan(base_change(resource_type)))))

    def test_noop_privilege_resource_does_not_hold(self):
        packet = evaluate(plan(base_change("aws_iam_policy", ["no-op"])))
        self.assertEqual(packet["decision"], "ready_for_human_review")

    def test_public_ipv4_ipv6_and_wildcard_hold(self):
        for cidr in ("0.0.0.0/0", "::/0", "*"):
            with self.subTest(cidr=cidr):
                change = base_change("aws_security_group_rule", ["create"], {"cidr_blocks": [cidr]})
                self.assertIn("PUBLIC_NETWORK_EXPOSURE", self.codes(evaluate(plan(change))))

    def test_non_network_resource_with_public_text_does_not_false_positive(self):
        change = base_change("aws_ssm_parameter", ["update"], {"description": "0.0.0.0/0"})
        self.assertNotIn("PUBLIC_NETWORK_EXPOSURE", self.codes(evaluate(plan(change))))

    def test_s3_public_access_controls_must_all_be_true(self):
        secure = {name: True for name in (
            "block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"
        )}
        packet = evaluate(plan(base_change("aws_s3_bucket_public_access_block", ["update"], secure)))
        self.assertNotIn("S3_PUBLIC_GUARD_WEAKENED", self.codes(packet))
        for field in secure:
            weakened = copy.deepcopy(secure)
            weakened[field] = False
            packet = evaluate(plan(base_change("aws_s3_bucket_public_access_block", ["update"], weakened)))
            self.assertIn("S3_PUBLIC_GUARD_WEAKENED", self.codes(packet))

    def test_aks_requires_private_api_and_disabled_local_accounts(self):
        secure = {"private_cluster_enabled": True, "local_account_disabled": True}
        self.assertEqual(evaluate(plan(base_change("azurerm_kubernetes_cluster", ["update"], secure)))["decision"], "ready_for_human_review")
        for field, code in (("private_cluster_enabled", "AKS_PUBLIC_CONTROL_PLANE"),
                            ("local_account_disabled", "AKS_LOCAL_ACCOUNTS_ENABLED")):
            value = copy.deepcopy(secure)
            value[field] = False
            self.assertIn(code, self.codes(evaluate(plan(base_change("azurerm_kubernetes_cluster", ["update"], value)))))

    def test_change_limit_is_policy_hold(self):
        packet = evaluate(plan(base_change(), base_change("aws_cloudwatch_metric_alarm")), max_changes=1)
        self.assertIn("CHANGE_LIMIT_EXCEEDED", self.codes(packet))
        self.assertEqual(packet["decision"], "hold")

    def test_digest_is_deterministic_and_binds_values(self):
        first = plan(base_change(after={"value": "one"}))
        reordered = {"resource_changes": first["resource_changes"], "terraform_version": "1.9.8", "format_version": "1.2"}
        changed = plan(base_change(after={"value": "two"}))
        self.assertEqual(evaluate(first)["plan_sha256"], evaluate(reordered)["plan_sha256"])
        self.assertNotEqual(evaluate(first)["plan_sha256"], evaluate(changed)["plan_sha256"])

    def test_unknown_and_impossible_actions_fail_closed(self):
        for actions in (["migrate"], ["create", "update"], [], [True]):
            with self.subTest(actions=actions), self.assertRaises(InvalidPlan):
                evaluate(plan(base_change(actions=actions)))

    def test_missing_required_metadata_fails_closed(self):
        for key in ("format_version", "terraform_version", "resource_changes"):
            value = plan(base_change())
            del value[key]
            with self.subTest(key=key), self.assertRaises(InvalidPlan):
                evaluate(value)

    def test_input_caps_and_max_changes_validation(self):
        with self.assertRaises(InvalidPlan):
            evaluate(plan(*[base_change(f"aws_instance.t{i}") for i in range(1001)]))
        for limit in (0, True, 1001):
            with self.subTest(limit=limit), self.assertRaises(InvalidPlan):
                evaluate(plan(), max_changes=limit)

    def test_strict_loader_rejects_duplicate_nonfinite_and_large_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            for raw in ('{"a":1,"a":2}', '{"a":NaN}', ' ' * 5_000_001):
                path.write_text(raw)
                with self.subTest(prefix=raw[:12]), self.assertRaises(InvalidPlan):
                    load_json(path)

    def test_invalid_cli_never_echoes_input_or_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SECRET-PATH.json"
            path.write_text('{"token":"DO-NOT-LOG"}')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main([str(path)])
            self.assertEqual(status, 2)
            self.assertNotIn("DO-NOT-LOG", output.getvalue())
            self.assertNotIn("SECRET-PATH", output.getvalue())

    def test_cli_exit_codes_and_json(self):
        cases = (("safe-plan.json", 0, "ready_for_human_review"),
                 ("risky-plan.json", 1, "hold"))
        for filename, status, decision in cases:
            run = subprocess.run(
                [sys.executable, str(ROOT / "changesentry.py"), str(ROOT / "samples" / filename)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(run.returncode, status, run.stderr)
            output = json.loads(run.stdout)
            self.assertEqual(output["decision"], decision)
            self.assertFalse(output["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
