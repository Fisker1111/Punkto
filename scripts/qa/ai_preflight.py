#!/usr/bin/env python3
"""Read-only Punkti 0.6 /ai, bootstrap, and static publication preflight.

This cannot establish signed-record correctness, independent peer replication,
safe public POST handling, long-term retention or genuine blind AI usability.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from urllib.parse import urlparse

HASH = re.compile(r"^[a-f0-9]{64}$")
GEO = set("0123456789bcdefghjkmnpqrstuvwxyz")
PUB = "punkti/pub/0.6"
BOOT = "punkti/bootstrap/1"
LIMIT = 4 * 1024 * 1024


def get_http(url, timeout=8):
    if urlparse(url).scheme not in ("https", "http"):
        raise ValueError("expected HTTP(S) URL")
    req = urllib.request.Request(url, headers={"User-Agent": "Punkto-AI-Preflight/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        if res.status != 200:
            raise ValueError("HTTP status {}".format(res.status))
        data = res.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("response exceeds 4 MiB preflight bound")
    return data


def read_json(fetch, url):
    obj = json.loads(fetch(url).decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def validate_nodes(obj):
    if obj.get("v") != BOOT or not isinstance(obj.get("nodes"), list) or not obj["nodes"]:
        raise ValueError("invalid Punkti bootstrap")
    bases = set()
    for n in obj["nodes"]:
        if not isinstance(n, dict) or any(not isinstance(n.get(k), str) or not n[k] for k in ("id", "base", "publication")):
            raise ValueError("invalid node descriptor")
        for k in ("base", "publication", "submit", "index"):
            if k in n and (not isinstance(n[k], str) or urlparse(n[k]).scheme not in ("http", "https")):
                raise ValueError("invalid {} URL".format(k))
        if n["base"] in bases:
            raise ValueError("duplicate node base URL")
        bases.add(n["base"])
    return obj["nodes"]


def validate_publication(fetch, node):
    publication = node["publication"].rstrip("/")
    root = read_json(fetch, publication + "/root.json")
    if set(root) != {"v", "head", "seq"} or root["v"] != PUB:
        raise ValueError("invalid publication root")
    head, seq = root["head"], root["seq"]
    if not isinstance(head, str) or not HASH.fullmatch(head) or type(seq) is not int or seq < 1:
        raise ValueError("invalid root head or seq")
    raw_manifest = fetch(publication + "/manifests/" + head + ".json")
    if hashlib.sha256(raw_manifest).hexdigest() != head:
        raise ValueError("manifest SHA256 mismatch")
    manifest = json.loads(raw_manifest.decode("utf-8"))
    if not isinstance(manifest, dict) or manifest.get("v") != PUB or type(manifest.get("seq")) is not int or manifest["seq"] != seq:
        raise ValueError("invalid manifest profile or sequence")
    if type(manifest.get("record_count")) is not int or manifest["record_count"] < 0:
        raise ValueError("invalid manifest record count")
    index = manifest.get("index")
    if not isinstance(index, dict):
        raise ValueError("missing spatial index")
    for prefix, sha in index.items():
        if len(prefix) != 2 or any(c not in GEO for c in prefix):
            raise ValueError("non-spatial index prefix {!r}".format(prefix))
        if not isinstance(sha, str) or not HASH.fullmatch(sha):
            raise ValueError("invalid spatial shard hash")
    result = {
        "id": node["id"], "base": node["base"], "head": head, "seq": seq,
        "record_count": manifest["record_count"], "occupied_prefixes": len(index),
        "has_submit": bool(node.get("submit")), "has_discovery_index": bool(node.get("index")),
    }
    if node.get("index"):
        discovery = read_json(fetch, node["index"])
        source = discovery.get("source")
        if not isinstance(source, dict) or source.get("head") != head or source.get("seq") != seq:
            raise ValueError("discovery index is not tied to the current publication head")
        result["discovery_head_matches"] = True
    return result


def run_checks(fetch, ai_url, bootstrap_url, min_nodes=2, require_index=True):
    report = {"test": "punkti-ai-readonly-preflight-v0.6",
              "read_only": True, "is_end_to_end_proof": False,
              "checks": {}, "nodes": []}
    try:
        ai = fetch(ai_url).decode("utf-8")
        if "Punkto" not in ai or "nodes.json" not in ai:
            raise ValueError("/ai does not document basic bootstrap")
        if any(p in ai for p in (
            "write an unanchored atom",
            "Omit <code>--h</code> for an unanchored reply",
            "Unanchored:</p>",
        )):
            raise ValueError("stale /ai recommends unanchored atom submission")
        report["checks"]["ai"] = "PASS"
    except Exception as exc:
        report["checks"]["ai"] = "FAIL: " + str(exc)
    try:
        nodes = validate_nodes(read_json(fetch, bootstrap_url))
        report["checks"]["bootstrap"] = "PASS"
    except Exception as exc:
        nodes = []
        report["checks"]["bootstrap"] = "FAIL: " + str(exc)
    report["checks"]["nodes"] = "PASS" if len(nodes) >= min_nodes else "FAIL: {} node(s), expected {}".format(len(nodes), min_nodes)
    report["checks"]["discovery_advertised"] = (
        "PASS" if not require_index or any(node.get("index") for node in nodes)
        else "FAIL: no static discovery index advertised"
    )
    for node in nodes:
        try:
            report["nodes"].append(dict(validate_publication(fetch, node), status="PASS"))
        except Exception as exc:
            report["nodes"].append({"id": node["id"], "status": "FAIL", "error": str(exc)})
    report["pass"] = (
        all(value == "PASS" for value in report["checks"].values())
        and all(node["status"] == "PASS" for node in report["nodes"])
    )
    report["limits"] = (
        "This only checks /ai, bootstrap, root/manifest SHA256, and index-head coherence. "
        "It does not validate signed R, submit, multi-node replication, or persistence."
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-url", default="https://punkto.xyz/ai")
    parser.add_argument("--nodes-url", default="https://punkto.xyz/nodes.json")
    parser.add_argument("--min-nodes", type=int, default=2)
    parser.add_argument("--no-require-discovery", action="store_true")
    parser.add_argument("--timeout", type=int, default=8)
    args = parser.parse_args()
    result = run_checks(lambda url: get_http(url, args.timeout), args.ai_url,
                        args.nodes_url, args.min_nodes, not args.no_require_discovery)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
