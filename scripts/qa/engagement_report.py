#!/usr/bin/env python3
"""Audit metadata for Punkto first-engagement pilot; NOT a cryptographic verifier.

A passing metadata report proves no remote identity, node independence, meaningful
conversation, honest AI origin, genuine signature or retention. Examine real
signed R bytes and actual client/server traces before claiming those outcomes.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HEX = re.compile(r"^[0-9a-f]{64}$")
MID = re.compile(r"^punkti/0\.6:[0-9a-f]{64}$")
GEO = re.compile(r"^[0123456789bcdefghjkmnpqrstuvwxyz]{4,12}$")
Z = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")
PROFILE = "punkto/engagement-ledger/1"


class InvalidLedger(ValueError):
    pass


def require(ok, msg):
    if not ok:
        raise InvalidLedger(msg)


def valid_hash(x):
    return isinstance(x, str) and bool(HEX.fullmatch(x))


def valid_mid(x):
    return isinstance(x, str) and bool(MID.fullmatch(x))


def valid_h(h):
    if not isinstance(h, str) or len(h) > 32 or "_" not in h:
        return False
    xy, z = h.split("_", 1)
    return bool(GEO.fullmatch(xy) and Z.fullmatch(z) and z != "-0")


def identifier(item, name):
    value = item.get(name)
    require(isinstance(value, str) and 1 <= len(value) <= 100 and
            all(c.isalnum() or c in "-_:." for c in value),
            "invalid " + name)
    return value


def hash_field(item, name):
    value = item.get(name)
    require(valid_hash(value), "invalid " + name)
    return value


def summarize(data):
    require(isinstance(data, dict) and data.get("v") == PROFILE,
            "wrong ledger profile")
    environment = data.get("environment")
    require(environment in ("isolated-staging", "public-controlled", "synthetic"),
            "unrecognized environment")
    runs, atoms, custody = (data.get(k) for k in ("runs", "atoms", "custody"))
    require(all(isinstance(x, list) for x in (runs, atoms, custody)),
            "runs, atoms and custody must be arrays")
    require(len(runs) <= 10000 and len(atoms) <= 100000 and len(custody) <= 10000,
            "excessive evidence file")
    byrun = {}
    for run in runs:
        require(isinstance(run, dict), "invalid run")
        run_id = identifier(run, "run_id")
        op = identifier(run, "operator_id")
        require(isinstance(run.get("model"), str) and
                1 <= len(run["model"]) <= 200, "invalid model label")
        hash_field(run, "read_trace_sha256")
        require(run_id not in byrun, "duplicate agent run ID")
        byrun[run_id] = op

    bymid = defaultdict(list)
    byrecord = {}
    for atom in atoms:
        require(isinstance(atom, dict), "invalid atom evidence")
        mid, record, h = atom.get("mid"), atom.get("record_sha256"), atom.get("h")
        require(valid_mid(mid) and valid_hash(record) and valid_h(h),
                "invalid MID, canonical h or R SHA256")
        run_id = identifier(atom, "author_run_id")
        require(run_id in byrun, "atom references an unobserved AI run")
        hash_field(atom, "verification_trace_sha256")
        require(record not in byrecord, "duplicate canonical R evidence")
        byrecord[record] = atom
        bymid[mid].append(atom)
        if "reply_to_mid" in atom:
            require(valid_mid(atom["reply_to_mid"]) and
                    atom["reply_to_mid"] != mid, "invalid reply MID")

    # Candidate discussion: signed-looking root + a reply from another
    # observed run, at the *exact* same address. Does not assess relevance.
    candidate_threads = set()
    ambiguous_refs = 0
    for atom in atoms:
        parentmid = atom.get("reply_to_mid")
        if parentmid is None:
            continue
        parents = bymid.get(parentmid, [])
        if len(parents) != 1:
            ambiguous_refs += 1
            continue
        parent = parents[0]
        if parent["h"] != atom["h"]:
            continue
        if parent["author_run_id"] == atom["author_run_id"]:
            continue
        # Traverse to the root of this thread, detecting cycles and
        # ambiguous MID references without assigning thread semantics to L3.
        seen = set()
        current = parent
        while current.get("reply_to_mid") is not None:
            if current["mid"] in seen:
                break
            seen.add(current["mid"])
            ancestors = bymid.get(current["reply_to_mid"], [])
            if len(ancestors) != 1 or ancestors[0]["h"] != atom["h"]:
                break
            current = ancestors[0]
        else:
            candidate_threads.add((current["h"], current["mid"]))

    # A candidate preservation pair must name the same exact raw R hash,
    # preserved by separate declared operators, with claimed restored digest.
    custodians = defaultdict(set)
    for receipt in custody:
        require(isinstance(receipt, dict), "invalid custody receipt")
        op = identifier(receipt, "operator_id")
        identifier(receipt, "node_id")
        mid = receipt.get("source_mid")
        require(valid_mid(mid), "invalid custody source MID")
        sha = hash_field(receipt, "record_sha256")
        restored = hash_field(receipt, "restored_record_sha256")
        hash_field(receipt, "fetch_trace_sha256")
        hash_field(receipt, "restore_trace_sha256")
        require(restored == sha, "restored record differs from source digest")
        require(sha in byrecord and byrecord[sha]["mid"] == mid,
                "custody receipt lacks a matching candidate atom")
        custodians[(mid, sha)].add(op)

    shared_assets = sum(len(ops) >= 2 for ops in custodians.values())
    operators = set(byrun.values())
    meets_counts = (
        len(byrun) >= 10 and len(operators) >= 3 and
        len(candidate_threads) >= 3 and shared_assets >= 1 and
        ambiguous_refs == 0
    )
    return {
        "v": PROFILE,
        "environment": environment,
        "observed_agent_runs_claimed": len(byrun),
        "distinct_agent_operators_claimed": len(operators),
        "record_entries_claimed": len(atoms),
        "candidate_discussions_with_cross_run_replies": len(candidate_threads),
        "ambiguous_reply_references": ambiguous_refs,
        "assets_with_two_declared_independent_custodians": shared_assets,
        "candidate_metrics_complete": meets_counts and environment != "synthetic",
        "cryptographic_verification_performed": False,
        "independent_operator_verification_performed": False,
        "semantic_quality_review_performed": False,
        "public_launch_approved": False,
        "note": ("These are untrusted self-reported evidence metadata counts only. "
                 "Verify actual signed R, raw SHA256, agent provenance, independent "
                 "operators, safe writes, semantics and restore traces before launch."),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="local JSON evidence file")
    parser.add_argument("--require-targets", action="store_true",
                        help="fail if target counts are incomplete; never implies launch approval")
    args = parser.parse_args(argv)
    try:
        result = summarize(json.loads(args.ledger.read_text(encoding="utf-8")))
    except (InvalidLedger, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc), "valid_ledger": False}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_targets and not result["candidate_metrics_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
