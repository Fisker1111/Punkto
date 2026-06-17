#!/usr/bin/env python3
"""
Point 4 — Atom log format and fast-forward persistence tests.

Tests pure Buffer storage functions directly (no HTTP handler instantiation).

Cases:
  A. New accepted atom receives atom_id and cursor in log record.
  B. Two unique atoms receive monotonically increasing cursors.
  C. Duplicate atom is idempotent: no second log record/cursor.
  D. New-format log survives restart: same atom_id and cursor restored.
  E. Legacy raw-atom log loads without crashing.
  F. After loading legacy entries, new entries continue with safe increasing cursors.
  G. /feed?since=0 (cursor=0) returns all current records.
  H. /feed?since=<first_cursor> returns only later records.
  I. Corrupt log line is skipped; relay loads remaining atoms normally.
"""

import os
import sys
import json
import time
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("PUNKTO_REQUIRE_SIG", "false")

from relay import Buffer, compute_atom_id

results = []


def check(label: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))
    results.append((label, passed))
    return passed


def make_atom(content: str = "test atom", offset_ms: int = 0) -> dict:
    return {
        "punkto": "p:test00000000",
        "content": content,
        "t": int(time.time() * 1000) + offset_ms,
    }


def read_log_records(path: str) -> list:
    """Read log file and return list of parsed JSON records."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    records.append(None)  # corrupt
    return records


print("=" * 60)
print("POINT 4 — Atom log format and fast-forward tests")
print("=" * 60)

# ── A: New accepted atom receives atom_id and cursor in log record ──────────
print("\nA. New atom gets atom_id and cursor in log record")
tmpdir_a = tempfile.mkdtemp(prefix="punkto_test_a_")
try:
    log_path = os.path.join(tmpdir_a, "atoms.log.jsonl")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    atom_a = make_atom("atom A")
    atom_id_a, was_new = buf.append(atom_a)
    check("A. was_new=True", was_new, f"was_new={was_new}")
    records = read_log_records(log_path)
    check("A. log has 1 record", len(records) == 1, f"{len(records)} record(s)")
    rec = records[0]
    check("A. record has 'log_seq' key", "log_seq" in rec, str(list(rec.keys())))
    check("A. record has 'atom_id' key", "atom_id" in rec, str(list(rec.keys())))
    check("A. record has 'atom' key", "atom" in rec, str(list(rec.keys())))
    check("A. atom_id matches computed", rec.get("atom_id") == atom_id_a, f"{rec.get('atom_id')[:12]}")
    check("A. log_seq is integer >= 1", isinstance(rec.get("log_seq"), int) and rec["log_seq"] >= 1, f"log_seq={rec.get('log_seq')}")
finally:
    shutil.rmtree(tmpdir_a)

# ── B: Two unique atoms receive increasing cursors ───────────────────────────
print("\nB. Two unique atoms get monotonically increasing cursors")
tmpdir_b = tempfile.mkdtemp(prefix="punkto_test_b_")
try:
    log_path = os.path.join(tmpdir_b, "atoms.log.jsonl")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    id1, _ = buf.append(make_atom("atom B1", offset_ms=0))
    id2, _ = buf.append(make_atom("atom B2", offset_ms=1))
    records = read_log_records(log_path)
    check("B. log has 2 records", len(records) == 2, f"{len(records)} record(s)")
    c1 = records[0].get("log_seq", -1)
    c2 = records[1].get("log_seq", -1)
    check("B. log_seq2 > log_seq1", c2 > c1, f"log_seq1={c1} log_seq2={c2}")
finally:
    shutil.rmtree(tmpdir_b)

# ── C: Duplicate atom is idempotent ──────────────────────────────────────────
print("\nC. Duplicate atom is idempotent (no second cursor)")
tmpdir_c = tempfile.mkdtemp(prefix="punkto_test_c_")
try:
    log_path = os.path.join(tmpdir_c, "atoms.log.jsonl")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    atom_c = make_atom("atom C")
    id1, new1 = buf.append(atom_c)
    id2, new2 = buf.append(atom_c)  # exact duplicate
    records = read_log_records(log_path)
    check("C. first append was_new=True", new1, f"new1={new1}")
    check("C. second append was_new=False", not new2, f"new2={new2}")
    check("C. log has exactly 1 record", len(records) == 1, f"{len(records)} record(s)")
    check("C. both calls return same atom_id", id1 == id2, f"id1={id1[:12]} id2={id2[:12]}")
finally:
    shutil.rmtree(tmpdir_c)

# ── D: New-format log survives restart ───────────────────────────────────────
print("\nD. New-format log survives relay restart (atom_id and cursor preserved)")
tmpdir_d = tempfile.mkdtemp(prefix="punkto_test_d_")
try:
    log_path = os.path.join(tmpdir_d, "atoms.log.jsonl")
    # First session
    buf1 = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf1.load()
    atom_d = make_atom("atom D")
    orig_id, _ = buf1.append(atom_d)
    records_before = read_log_records(log_path)
    orig_cursor = records_before[0]["log_seq"]
    # Simulated restart: new Buffer instance, same log file
    buf2 = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf2.load()
    check("D. buffer size=1 after restart", buf2.size() == 1, f"size={buf2.size()}")
    check("D. atom retrievable by id after restart", buf2.has(orig_id), f"has={buf2.has(orig_id)}")
    # New append after restart should use log_seq > orig_log_seq
    atom_d2 = make_atom("atom D2", offset_ms=1)
    new_id, _ = buf2.append(atom_d2)
    records_after = read_log_records(log_path)
    new_cursor = records_after[1]["log_seq"]
    check("D. new log_seq after restart > original log_seq", new_cursor > orig_cursor, f"orig={orig_cursor} new={new_cursor}")
finally:
    shutil.rmtree(tmpdir_d)

# ── E: Legacy raw-atom log loads without crashing ────────────────────────────
print("\nE. Legacy raw-atom log loads without crashing")
tmpdir_e = tempfile.mkdtemp(prefix="punkto_test_e_")
try:
    log_path = os.path.join(tmpdir_e, "atoms.log.jsonl")
    # Write legacy raw atoms
    legacy_atoms = [
        {"punkto": "p:test00000000", "content": "legacy 1", "t": int(time.time() * 1000)},
        {"punkto": "p:test00000000", "content": "legacy 2", "t": int(time.time() * 1000) + 1},
    ]
    with open(log_path, "w") as f:
        for a in legacy_atoms:
            f.write(json.dumps(a) + "\n")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    check("E. loads without exception", True, "no crash")
    check("E. buffer has 2 legacy atoms", buf.size() == 2, f"size={buf.size()}")
    check("E. corrupt_lines=0 for legacy", buf.corrupt_lines() == 0, f"corrupt={buf.corrupt_lines()}")
finally:
    shutil.rmtree(tmpdir_e)

# ── F: After legacy load, new atoms continue with safe cursors ───────────────
print("\nF. After loading legacy entries, new entries continue with safe increasing cursors")
tmpdir_f = tempfile.mkdtemp(prefix="punkto_test_f_")
try:
    log_path = os.path.join(tmpdir_f, "atoms.log.jsonl")
    # Write legacy raw atom
    legacy = {"punkto": "p:test00000000", "content": "legacy atom", "t": int(time.time() * 1000)}
    with open(log_path, "w") as f:
        f.write(json.dumps(legacy) + "\n")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    # Append a new atom after loading legacy
    new_atom = make_atom("new after legacy", offset_ms=2)
    new_id, _ = buf.append(new_atom)
    records = read_log_records(log_path)
    # Legacy line is raw dict; new line is wrapped
    check("F. log has 2 lines total", len(records) == 2, f"{len(records)} lines")
    wrapped = records[1]
    check("F. new record is wrapped format", "log_seq" in wrapped and "atom_id" in wrapped and "atom" in wrapped,
          str(list(wrapped.keys())))
    check("F. new log_seq >= 1", wrapped.get("log_seq", 0) >= 1, f"log_seq={wrapped.get('log_seq')}")
finally:
    shutil.rmtree(tmpdir_f)

# ── G: feed_since(0) returns all records ─────────────────────────────────────
print("\nG. feed_since(cursor=0) returns all public atoms")
tmpdir_g = tempfile.mkdtemp(prefix="punkto_test_g_")
try:
    log_path = os.path.join(tmpdir_g, "atoms.log.jsonl")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    buf.append(make_atom("G1", 0))
    buf.append(make_atom("G2", 1))
    buf.append(make_atom("G3", 2))
    atoms, new_cursor, underflow = buf.feed_since(0)
    check("G. feed_since(0) returns 3 atoms", len(atoms) == 3, f"{len(atoms)} atom(s)")
    check("G. new_cursor > 0", new_cursor > 0, f"new_cursor={new_cursor}")
    check("G. underflow=False", not underflow, f"underflow={underflow}")
finally:
    shutil.rmtree(tmpdir_g)

# ── H: feed_since(first_cursor) returns only later records ───────────────────
print("\nH. feed_since(first_cursor) returns only atoms after that cursor")
tmpdir_h = tempfile.mkdtemp(prefix="punkto_test_h_")
try:
    log_path = os.path.join(tmpdir_h, "atoms.log.jsonl")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    buf.append(make_atom("H1", 0))
    # Get cursor after first atom
    _, cursor_after_h1, _ = buf.feed_since(0)
    buf.append(make_atom("H2", 1))
    buf.append(make_atom("H3", 2))
    # Since cursor_after_h1 is the byte offset after H1, feed should return H2 and H3
    atoms_since, new_cursor2, underflow2 = buf.feed_since(cursor_after_h1)
    check("H. feed_since(after H1) returns 2 atoms", len(atoms_since) == 2, f"{len(atoms_since)} atom(s)")
    check("H. underflow=False", not underflow2, f"underflow={underflow2}")
finally:
    shutil.rmtree(tmpdir_h)

# ── I: Corrupt log line is skipped ───────────────────────────────────────────
print("\nI. Corrupt log line is skipped; relay loads remaining atoms normally")
tmpdir_i = tempfile.mkdtemp(prefix="punkto_test_i_")
try:
    log_path = os.path.join(tmpdir_i, "atoms.log.jsonl")
    # Write: valid wrapped, corrupt line, valid wrapped
    now_ms = int(time.time() * 1000)
    valid1 = {"log_seq": 1, "atom_id": compute_atom_id({"punkto": "p:test00000000", "content": "I1", "t": now_ms}),
              "atom": {"punkto": "p:test00000000", "content": "I1", "t": now_ms}}
    valid2 = {"log_seq": 2, "atom_id": compute_atom_id({"punkto": "p:test00000000", "content": "I2", "t": now_ms + 1}),
              "atom": {"punkto": "p:test00000000", "content": "I2", "t": now_ms + 1}}
    with open(log_path, "w") as f:
        f.write(json.dumps(valid1) + "\n")
        f.write("THIS IS NOT JSON {{{ CORRUPT\n")
        f.write(json.dumps(valid2) + "\n")
    buf = Buffer(log_path, max_atoms=1000, max_hours=24)
    buf.load()
    check("I. loads without exception", True, "no crash")
    check("I. corrupt_lines=1", buf.corrupt_lines() == 1, f"corrupt={buf.corrupt_lines()}")
    check("I. buffer has 2 valid atoms", buf.size() == 2, f"size={buf.size()}")
finally:
    shutil.rmtree(tmpdir_i)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, p in results if p)
failed = sum(1 for _, p in results if not p)
total = len(results)
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("STATUS: ALL PASS")
else:
    print("STATUS: FAIL")
    for label, p in results:
        if not p:
            print(f"  FAILED: {label}")
    sys.exit(1)
