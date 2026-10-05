import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta

from rotation import Invalid, load, main, plan, retirement_report, stamp

ROOT = Path(__file__).parent
START = stamp("2026-10-05T10:00:00Z")


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.inventory = load(ROOT / "samples/inventory.json")

    def evidence(self):
        p = plan(self.inventory, START)
        return {"plan_id": p["plan_id"], "observations": [
            {"consumer": c["id"], "version": "v2", "healthy": True,
             "observed_at": p["finish_at"]} for c in self.inventory["consumers"]]}

    def report(self, evidence):
        finish = stamp(plan(self.inventory, START)["finish_at"])
        return retirement_report(self.inventory, START, evidence, finish + timedelta(seconds=30))

    def test_dependency_and_capacity_schedule(self):
        p = plan(self.inventory, START)
        self.assertEqual([w["consumers"] for w in p["waves"]],
                         [["connection-proxy"], ["checkout-api"], ["refund-worker"], ["reconciliation"]])
        self.assertEqual(p["estimated_seconds"], 720)
        self.assertEqual(p["finish_at"], "2026-10-05T10:12:00Z")
        self.assertFalse(p["execution_authorized"])

    def test_parallel_wave_uses_max_duration(self):
        self.inventory["teams"]["payments"] = 2
        p = plan(self.inventory, START)
        self.assertEqual(p["waves"][1]["consumers"], ["checkout-api", "refund-worker"])
        self.assertEqual(p["estimated_seconds"], 540)

    def test_expiry_boundary(self):
        self.inventory["expires_at"] = "2026-10-05T10:22:00Z"
        self.assertEqual(plan(self.inventory, START)["decision"], "ready_for_review")
        self.inventory["expires_at"] = "2026-10-05T10:21:59Z"
        self.assertEqual(plan(self.inventory, START)["decision"], "hold")

    def test_cycles_and_unknown_dependencies(self):
        for deps in (["reconciliation"], ["missing"], ["connection-proxy"]):
            with self.subTest(deps=deps):
                self.inventory["consumers"][0]["depends_on"] = deps
                with self.assertRaises(Invalid):
                    plan(self.inventory, START)

    def test_bad_inventory_rejected(self):
        for edit in (lambda m: m.update(token="DO-NOT-LOG"),
                     lambda m: m["teams"].update(platform=True),
                     lambda m: m.update(consumers=[]),
                     lambda m: m["consumers"].append(copy.deepcopy(m["consumers"][0])),
                     lambda m: m.update(old_version="v2"),
                     lambda m: m["consumers"][0].update(rollout_seconds=-1),
                     lambda m: m["consumers"][0].update(team="unknown")):
            m = copy.deepcopy(self.inventory)
            edit(m)
            with self.assertRaises(Invalid):
                plan(m, START)

    def test_binding_covers_manifest_and_start(self):
        original = plan(self.inventory, START)["plan_id"]
        self.assertNotEqual(original, plan(self.inventory, START + timedelta(seconds=1))["plan_id"])
        self.inventory["environment"] = "other"
        self.assertNotEqual(original, plan(self.inventory, START)["plan_id"])

    def test_all_consumers_healthy_is_review_only(self):
        r = self.report(self.evidence())
        self.assertEqual(r["decision"], "ready_for_review")
        self.assertFalse(r["execution_authorized"])

    def test_missing_extra_and_wrong_plan_hold(self):
        for mutation in (lambda e: e["observations"].pop(),
                         lambda e: e.update(plan_id="wrong"),
                         lambda e: e["observations"].append({"consumer": "extra", "version": "v2",
                                                              "healthy": True, "observed_at": "2026-10-05T10:12:00Z"})):
            e = self.evidence()
            mutation(e)
            self.assertEqual(self.report(e)["decision"], "hold")

    def test_unhealthy_old_version_future_and_pre_finish_hold(self):
        for changes in ({"healthy": False}, {"version": "v1"},
                        {"observed_at": "2026-10-05T10:13:00Z"},
                        {"observed_at": "2026-10-05T10:11:59Z"}):
            e = self.evidence()
            e["observations"][0].update(changes)
            self.assertEqual(self.report(e)["decision"], "hold")

    def test_freshness_boundary_and_current_expiry(self):
        e = self.evidence()
        finish = stamp(plan(self.inventory, START)["finish_at"])
        for seconds, decision in ((300, "ready_for_review"), (301, "hold"), (20000, "hold")):
            r = retirement_report(self.inventory, START, e, finish + timedelta(seconds=seconds))
            self.assertEqual(r["decision"], decision)

    def test_duplicate_and_non_boolean_evidence_invalid(self):
        e = self.evidence()
        e["observations"].append(e["observations"][0])
        with self.assertRaises(Invalid):
            self.report(e)
        e = self.evidence()
        e["observations"][0]["healthy"] = "true"
        with self.assertRaises(Invalid):
            self.report(e)

    def test_strict_json_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', ' ' * 1_000_001):
                path.write_text(raw)
                with self.assertRaises(Invalid):
                    load(path)

    def test_naive_timestamp_invalid(self):
        with self.assertRaises(Invalid):
            stamp("2026-10-05T10:00:00")

    def test_cli_does_not_echo_invalid_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text('{"password":"DO-NOT-LOG"}')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main([str(path), "--start-at", "2026-10-05T10:00:00Z"])
            self.assertEqual(status, 2)
            self.assertNotIn("DO-NOT-LOG", output.getvalue())
            self.assertFalse(json.loads(output.getvalue())["execution_authorized"])

    def test_cli_end_to_end_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            for expiry, expected in (("2026-10-05T13:00:00Z", 0), ("2026-10-05T10:00:00Z", 1)):
                self.inventory["expires_at"] = expiry
                path.write_text(json.dumps(self.inventory))
                run = subprocess.run([sys.executable, str(ROOT / "rotation.py"), str(path),
                                      "--start-at", "2026-10-05T10:00:00Z"], capture_output=True, text=True)
                self.assertEqual(run.returncode, expected, run.stderr)
                self.assertFalse(json.loads(run.stdout)["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
