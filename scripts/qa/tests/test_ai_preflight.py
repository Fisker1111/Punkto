"""Read-only fixture tests for ai_preflight; no network or writes required."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "ai_preflight.py"
spec = importlib.util.spec_from_file_location("ai_preflight", path)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def raw(obj):
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def fixture(unanchored=False, corrupt=False, stale=False):
    base = "https://test.invalid"
    manifest = {
        "v": "punkti/pub/0.6", "seq": 1, "record_count": 1, "pack_count": 0,
        "prev": None, "index": {"~" if unanchored else "u3": "a" * 64},
    }
    content = raw(manifest)
    head = hashlib.sha256(content).hexdigest()
    nodes = [
        {"id": "node1", "base": "https://one.invalid", "publication": "https://one.invalid/pub",
         "index": "https://one.invalid/pub/discovery/index.json"},
        {"id": "node2", "base": "https://two.invalid", "publication": "https://two.invalid/pub",
         "index": "https://two.invalid/pub/discovery/index.json"},
    ]
    objects = {
        base + "/ai": b"<h1>Punkto</h1> Fetch nodes.json to explore.",
        base + "/nodes.json": raw({"v": "punkti/bootstrap/1", "nodes": nodes}),
    }
    for node in nodes:
        pub = node["publication"]
        objects[pub + "/root.json"] = raw({"v": "punkti/pub/0.6", "head": head, "seq": 1})
        objects[pub + "/manifests/" + head + ".json"] = content + (b" " if corrupt else b"")
        objects[node["index"]] = raw({"source": {"head": "f" * 64 if stale else head, "seq": 1}})
    return objects, base


class ReadinessTest(unittest.TestCase):
    def result(self, objects, base):
        return p.run_checks(lambda url: objects[url], base + "/ai", base + "/nodes.json")

    def test_good_two_node_static_fixture(self):
        objects, base = fixture()
        result = self.result(objects, base)
        self.assertTrue(result["pass"])
        self.assertEqual(len(result["nodes"]), 2)
        self.assertFalse(result["is_end_to_end_proof"])

    def test_unanchored_shard_is_rejected(self):
        objects, base = fixture(unanchored=True)
        result = self.result(objects, base)
        self.assertFalse(result["pass"])
        self.assertIn("non-spatial", result["nodes"][0]["error"])

    def test_corrupt_manifest_is_rejected(self):
        objects, base = fixture(corrupt=True)
        result = self.result(objects, base)
        self.assertFalse(result["pass"])
        self.assertIn("SHA256", result["nodes"][0]["error"])

    def test_discovery_head_mismatch_is_rejected(self):
        objects, base = fixture(stale=True)
        result = self.result(objects, base)
        self.assertFalse(result["pass"])
        self.assertIn("not tied", result["nodes"][0]["error"])

    def test_old_ai_page_is_rejected(self):
        objects, base = fixture()
        objects[base + "/ai"] = b"Punkto nodes.json: write an unanchored atom"
        result = self.result(objects, base)
        self.assertFalse(result["pass"])
        self.assertIn("unanchored", result["checks"]["ai"])

    def test_single_node_does_not_meet_two_node_gate(self):
        objects, base = fixture()
        bootstrap = json.loads(objects[base + "/nodes.json"])
        bootstrap["nodes"] = bootstrap["nodes"][:1]
        objects[base + "/nodes.json"] = raw(bootstrap)
        self.assertFalse(self.result(objects, base)["pass"])

    def test_duplicate_node_url_is_rejected(self):
        objects, base = fixture()
        bootstrap = json.loads(objects[base + "/nodes.json"])
        bootstrap["nodes"][1]["base"] = bootstrap["nodes"][0]["base"]
        objects[base + "/nodes.json"] = raw(bootstrap)
        result = self.result(objects, base)
        self.assertFalse(result["pass"])
        self.assertIn("duplicate", result["checks"]["bootstrap"])

    def test_missing_discovery_is_rejected(self):
        objects, base = fixture()
        bootstrap = json.loads(objects[base + "/nodes.json"])
        for node in bootstrap["nodes"]:
            node.pop("index", None)
        objects[base + "/nodes.json"] = raw(bootstrap)
        result = self.result(objects, base)
        self.assertFalse(result["pass"])
        self.assertIn("no static", result["checks"]["discovery_advertised"])


if __name__ == "__main__":
    unittest.main()
