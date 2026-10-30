"""Synthetic fixtures only. Never present these as real independent AIs."""
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "engagement_report.py"
spec = importlib.util.spec_from_file_location("engagement_report", file)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)

H = ["ge0q7k_0", "umgjh0_0", "9q8zhu_0"]


def h64(n):
    return format(n, "064x")


def fixture(environment="isolated-staging"):
    runs = [
        {
            "run_id": "agent-" + str(i),
            "operator_id": "op" + str(i % 3),
            "model": "synthetic-no-real-model",
            "read_trace_sha256": h64(300 + i),
        } for i in range(10)
    ]
    atoms = []
    for i, address in enumerate(H):
        root_mid = "punkti/0.6:" + h64(10 + 2 * i)
        atoms.append({
            "mid": root_mid, "h": address, "record_sha256": h64(110 + 2 * i),
            "verification_trace_sha256": h64(500 + i),
            "author_run_id": "agent-" + str(2 * i),
        })
        atoms.append({
            "mid": "punkti/0.6:" + h64(11 + 2 * i),
            "h": address, "record_sha256": h64(111 + 2 * i),
            "verification_trace_sha256": h64(600 + i),
            "author_run_id": "agent-" + str(2 * i + 1),
            "reply_to_mid": root_mid,
        })
    custody = [
        {"operator_id": "custodian-" + str(i), "node_id": "node" + str(i),
         "source_mid": atoms[0]["mid"],
         "record_sha256": atoms[0]["record_sha256"],
         "restored_record_sha256": atoms[0]["record_sha256"],
         "fetch_trace_sha256": h64(700+i),
         "restore_trace_sha256": h64(800+i)}
        for i in range(2)
    ]
    return {"v": reporter.PROFILE, "environment": environment,
            "runs": runs, "atoms": atoms, "custody": custody}


class EngagementReportTest(unittest.TestCase):
    def test_candidate_counts_only_do_not_prove_launch(self):
        report = reporter.summarize(fixture())
        self.assertEqual(report["observed_agent_runs_claimed"], 10)
        self.assertEqual(report["candidate_discussions_with_cross_run_replies"], 3)
        self.assertEqual(report["assets_with_two_declared_independent_custodians"], 1)
        self.assertTrue(report["candidate_metrics_complete"])
        self.assertFalse(report["cryptographic_verification_performed"])
        self.assertFalse(report["public_launch_approved"])

    def test_synthetic_never_claims_ready(self):
        self.assertFalse(reporter.summarize(fixture("synthetic"))["candidate_metrics_complete"])

    def test_no_automatic_claim_from_10_keys(self):
        f = fixture()
        for run in f["runs"]:
            run["operator_id"] = "same-operator"
        report = reporter.summarize(f)
        self.assertEqual(report["distinct_agent_operators_claimed"], 1)
        self.assertFalse(report["candidate_metrics_complete"])

    def test_one_custodian_cannot_count_as_two(self):
        f = fixture()
        f["custody"][1]["operator_id"] = f["custody"][0]["operator_id"]
        report = reporter.summarize(f)
        self.assertEqual(report["assets_with_two_declared_independent_custodians"], 0)
        self.assertFalse(report["candidate_metrics_complete"])

    def test_cross_address_reply_not_a_thread(self):
        f = fixture()
        f["atoms"][1]["h"] = "s00000_0"
        self.assertEqual(reporter.summarize(f)["candidate_discussions_with_cross_run_replies"], 2)

    def test_self_reply_does_not_count_as_discussion(self):
        f = fixture()
        f["atoms"][1]["author_run_id"] = f["atoms"][0]["author_run_id"]
        self.assertEqual(reporter.summarize(f)["candidate_discussions_with_cross_run_replies"], 2)

    def test_missing_parent_is_explicitly_flagged(self):
        f = fixture()
        f["atoms"][1]["reply_to_mid"] = "punkti/0.6:" + h64(999)
        report = reporter.summarize(f)
        self.assertEqual(report["ambiguous_reply_references"], 1)
        self.assertFalse(report["candidate_metrics_complete"])

    def test_duplicate_run_detected(self):
        f = fixture()
        f["runs"][1]["run_id"] = f["runs"][0]["run_id"]
        with self.assertRaisesRegex(reporter.InvalidLedger, "duplicate"):
            reporter.summarize(f)

    def test_canonical_xy_z_rejects_broken_spatial_values(self):
        for address in ("", "~", "ge0q7k_-0", "ge0q7k_023", "ge0q7k_0.0",
                        "ge0q7k_1.20", "GE0Q7K_0", "ge_0", "ge0q7k", "ge0q7k_1e2"):
            with self.subTest(address=address):
                self.assertFalse(reporter.valid_h(address))
        for address in H + ["ge0q7k_-0.5", "ge0q7k_23.025", "s00000_0"]:
            self.assertTrue(reporter.valid_h(address))

    def test_preservation_receipt_must_match_original_record_digest(self):
        f = fixture()
        f["custody"][0]["restored_record_sha256"] = h64(998)
        with self.assertRaisesRegex(reporter.InvalidLedger, "restored record differs"):
            reporter.summarize(f)

    def test_pilot_starts_with_no_evidence(self):
        report = reporter.summarize({
            "v": reporter.PROFILE, "environment": "isolated-staging",
            "runs": [], "atoms": [], "custody": []})
        self.assertFalse(report["candidate_metrics_complete"])
        self.assertEqual(report["observed_agent_runs_claimed"], 0)


if __name__ == "__main__":
    unittest.main()
