import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from drainscope import InputError, analyze, load_snapshot


NOW = datetime(2026, 10, 19, 9, 30, tzinfo=timezone.utc)


def snapshot():
    return {
        "schema_version": "1.0",
        "generated_at": "2026-10-19T09:29:00Z",
        "target_node": {"name": "worker-a", "zone": "zone-a"},
        "replacement_nodes": [
            {"name": "worker-b", "zone": "zone-b", "ready": True, "schedulable": True, "free": {"cpu_millicores": 2000, "memory_mib": 4096}},
            {"name": "worker-c", "zone": "zone-c", "ready": True, "schedulable": True, "free": {"cpu_millicores": 1000, "memory_mib": 2048}},
        ],
        "pods": [
            {
                "namespace": "shop", "name": "api-0", "phase": "Running",
                "owner": {"kind": "StatefulSet", "name": "api"},
                "controller": {"desired_replicas": 3, "ready_replicas": 3},
                "critical": False, "local_storage": [],
                "pdb": {"name": "api", "disruptions_allowed": 1},
                "requests": {"cpu_millicores": 500, "memory_mib": 512},
                "eligible_nodes": ["worker-b", "worker-c"], "peer_zones": ["zone-b", "zone-c"],
            },
            {
                "namespace": "monitoring", "name": "node-agent", "phase": "Running",
                "owner": {"kind": "DaemonSet", "name": "node-agent"}, "controller": None,
                "critical": False, "local_storage": [], "pdb": None,
                "requests": {"cpu_millicores": 50, "memory_mib": 64},
                "eligible_nodes": [], "peer_zones": [],
            },
        ],
    }


class AnalyzeTests(unittest.TestCase):
    def test_healthy_snapshot_is_reviewable_but_never_authorized(self):
        result = analyze(snapshot(), observed_at=NOW)
        self.assertEqual(result["decision"], "ready_for_human_review")
        self.assertFalse(result["drain_authorized"])
        self.assertEqual(result["eviction_candidates"], 1)

    def test_stale_snapshot_holds(self):
        data = snapshot(); data["generated_at"] = "2026-10-19T09:00:00Z"
        self.assertIn("SNAPSHOT_STALE", codes(analyze(data, observed_at=NOW)))

    def test_future_snapshot_is_invalid(self):
        data = snapshot(); data["generated_at"] = "2026-10-19T09:31:00Z"
        with self.assertRaises(InputError): analyze(data, observed_at=NOW)

    def test_unmanaged_pod_holds(self):
        data = snapshot(); data["pods"][0]["owner"] = None
        self.assertIn("UNMANAGED_POD", codes(analyze(data, observed_at=NOW)))

    def test_static_pod_holds(self):
        data = snapshot(); data["pods"][0]["owner"] = {"kind": "StaticPod", "name": "x"}
        self.assertIn("STATIC_POD", codes(analyze(data, observed_at=NOW)))

    def test_daemonset_is_not_eviction_candidate(self):
        result = analyze(snapshot(), observed_at=NOW)
        self.assertEqual(result["eviction_candidates"], 1)
        self.assertIn("DAEMONSET_IGNORED", {item["code"] for item in result["notes"]})

    def test_critical_pod_holds(self):
        data = snapshot(); data["pods"][0]["critical"] = True
        self.assertIn("CRITICAL_POD", codes(analyze(data, observed_at=NOW)))

    def test_degraded_controller_holds(self):
        data = snapshot(); data["pods"][0]["controller"]["ready_replicas"] = 2
        self.assertIn("CONTROLLER_DEGRADED", codes(analyze(data, observed_at=NOW)))

    def test_unbounded_emptydir_holds(self):
        data = snapshot(); data["pods"][0]["local_storage"] = [{"kind": "emptyDir", "size_limit_mib": None}]
        self.assertIn("LOCAL_STORAGE_RISK", codes(analyze(data, observed_at=NOW)))

    def test_bounded_emptydir_is_accepted(self):
        data = snapshot(); data["pods"][0]["local_storage"] = [{"kind": "emptyDir", "size_limit_mib": 128}]
        self.assertNotIn("LOCAL_STORAGE_RISK", codes(analyze(data, observed_at=NOW)))

    def test_pdb_is_aggregated_across_pods(self):
        data = snapshot(); second = deepcopy(data["pods"][0]); second["name"] = "api-1"; data["pods"].append(second)
        self.assertIn("PDB_BUDGET_EXCEEDED", codes(analyze(data, observed_at=NOW)))

    def test_inconsistent_pdb_evidence_is_invalid(self):
        data = snapshot(); second = deepcopy(data["pods"][0]); second["name"] = "api-1"; second["pdb"]["disruptions_allowed"] = 2; data["pods"].append(second)
        with self.assertRaises(InputError): analyze(data, observed_at=NOW)

    def test_no_eligible_node_holds(self):
        data = snapshot(); data["pods"][0]["eligible_nodes"] = ["missing"]
        self.assertIn("NO_ELIGIBLE_NODE", codes(analyze(data, observed_at=NOW)))

    def test_capacity_simulation_holds(self):
        data = snapshot(); data["replacement_nodes"][0]["free"]["memory_mib"] = 128; data["replacement_nodes"][1]["free"]["memory_mib"] = 128
        self.assertIn("INSUFFICIENT_REPLACEMENT_CAPACITY", codes(analyze(data, observed_at=NOW)))

    def test_topology_concentration_holds(self):
        data = snapshot(); data["pods"][0]["peer_zones"] = ["zone-a"]; data["pods"][0]["eligible_nodes"] = ["worker-b"]; data["replacement_nodes"][0]["zone"] = "zone-a"
        self.assertIn("TOPOLOGY_CONCENTRATION", codes(analyze(data, observed_at=NOW)))

    def test_terminal_pod_is_ignored(self):
        data = snapshot(); data["pods"][0]["phase"] = "Succeeded"
        result = analyze(data, observed_at=NOW)
        self.assertEqual(result["decision"], "ready_for_human_review")
        self.assertEqual(result["eviction_candidates"], 0)

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"; path.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
            with self.assertRaises(InputError): load_snapshot(path)

    def test_cli_exit_codes_and_redacted_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"; path.write_text(json.dumps(snapshot()))
            command = [sys.executable, "drainscope.py", str(path), "--at", "2026-10-19T09:30:00Z"]
            completed = subprocess.run(command, cwd=Path(__file__).parent, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0)
            self.assertFalse(json.loads(completed.stdout)["drain_authorized"])
            path.write_text("not-json SECRET")
            completed = subprocess.run(command, cwd=Path(__file__).parent, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 2)
            self.assertNotIn("SECRET", completed.stdout)


def codes(result):
    return {item["code"] for item in result["findings"]}


if __name__ == "__main__":
    unittest.main()
