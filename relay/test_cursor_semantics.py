#!/usr/bin/env python3
"""
Point 4 cursor semantics — integration test.

Starts a real local relay process and verifies byte-offset cursor semantics:

1. POST atom1, capture cursor from /feed response.
2. POST atom2.
3. GET /feed?since=<captured cursor> → exactly atom2 returned.
4. Restart relay, repeat step 3 → same result (cursor stable across restart).
5. Legacy raw-atom log: relay starts cleanly, new atoms get correct cursors.

Authoritative cursor model: byte offset in atoms.log.jsonl
(per punkto.sync.md §236 and Buffer.feed_since docstring)

Do not instantiate BaseRequestHandler or RelayHandler directly.
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import requests

PORT = 19877
BASE = f"http://127.0.0.1:{PORT}"
PASS = 0
FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> bool:
    global PASS, FAIL
    if cond:
        print(f"  [PASS] {label}" + (f": {detail}" if detail else ""))
        PASS += 1
    else:
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))
        FAIL += 1
    return cond


def wait_ready(timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def start_relay(data_dir: str, env_extra: dict = None) -> subprocess.Popen:
    data_subdir = os.path.join(data_dir, "data")
    os.makedirs(data_subdir, exist_ok=True)
    env = os.environ.copy()
    env["PUNKTO_DATA_DIR"] = data_subdir
    env["PUNKTO_PORT"] = str(PORT)
    env["PUNKTO_HOST"] = "127.0.0.1"
    env["PUNKTO_REQUIRE_SIG"] = "false"
    env["PUNKTO_SYNC_INTERVAL"] = "9999"
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(
        [sys.executable, "relay.py"],
        env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def stop_relay(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def make_atom(content: str) -> dict:
    return {
        "punkto": "p:test00000000",
        "content": content,
        "t": int(time.time() * 1000),
    }


print("=" * 60)
print("POINT 4 — Cursor semantics integration tests")
print("Authoritative model: byte-offset cursor (punkto.sync.md §236)")
print("=" * 60)

tmpdir = tempfile.mkdtemp(prefix="punkto_cursor_test_")
try:
    # ── 1. Start relay ─────────────────────────────────────────
    print("\n[Setup] Starting relay on port", PORT)
    proc = start_relay(tmpdir)
    if not check("Relay starts and /health returns 200", wait_ready()):
        stop_relay(proc)
        sys.exit(1)

    # ── Step 1: POST atom1, GET /feed, capture cursor ───────────
    print("\n1. POST atom1, capture cursor from /feed")
    r1 = requests.post(f"{BASE}/atom", json=make_atom("first atom"), timeout=5)
    check("1. POST atom1 returns 201", r1.status_code == 201, f"status={r1.status_code}")
    atom1_id = r1.json().get("atom_id", "")
    check("1. atom1_id present", bool(atom1_id), f"atom_id={atom1_id[:12]}")

    # Capture cursor from /feed
    feed0 = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
    cursor_after_1 = feed0.get("cursor", -1)
    check("1. /feed cursor is integer > 0", isinstance(cursor_after_1, int) and cursor_after_1 > 0,
          f"cursor={cursor_after_1}")
    # Check atom1 is in the feed (environment may have pre-existing atoms)
    feed_ids = {a.get("atom_id", a.get("id", "")) for a in feed0.get("atoms", [])}
    feed_contents = {a.get("content", "") for a in feed0.get("atoms", [])}
    check("1. atom1 is in feed",
          atom1_id in feed_ids or "first atom" in feed_contents,
          f"atom_ids={len(feed_ids)} items")

    # ── Step 2: POST atom2 ──────────────────────────────────────
    print("\n2. POST atom2")
    time.sleep(1)  # ensure distinct timestamp
    r2 = requests.post(f"{BASE}/atom", json=make_atom("second atom"), timeout=5)
    check("2. POST atom2 returns 201", r2.status_code == 201, f"status={r2.status_code}")
    atom2_id = r2.json().get("atom_id", "")
    check("2. atom2_id present and distinct", bool(atom2_id) and atom2_id != atom1_id,
          f"atom2_id={atom2_id[:12]}")

    # ── Step 3: GET /feed?since=<captured cursor> ───────────────
    print(f"\n3. GET /feed?since={cursor_after_1} → should return only atom2")
    feed_since = requests.get(f"{BASE}/feed?since={cursor_after_1}", timeout=5).json()
    atoms_since = feed_since.get("atoms", [])
    check("3. /feed?since=cursor returns exactly 1 atom", len(atoms_since) == 1,
          f"count={len(atoms_since)}")
    if atoms_since:
        returned_id = atoms_since[0].get("atom_id", atoms_since[0].get("id", ""))
        # atom_id may be in the atom dict itself or in a wrapper
        if not returned_id:
            # try content match
            returned_content = atoms_since[0].get("content", "")
            check("3. returned atom is atom2", returned_content == "second atom",
                  f"content={returned_content!r}")
        else:
            check("3. returned atom_id matches atom2", returned_id == atom2_id,
                  f"returned={returned_id[:12]} expected={atom2_id[:12]}")

    # ── Step 4: Restart relay, repeat step 3 ───────────────────
    print("\n4. Restart relay, repeat /feed?since=<cursor>")
    stop_relay(proc)
    time.sleep(0.5)
    proc = start_relay(tmpdir)
    check("4. Relay restarts and /health returns 200", wait_ready())

    feed_after_restart = requests.get(f"{BASE}/feed?since={cursor_after_1}", timeout=5).json()
    atoms_after_restart = feed_after_restart.get("atoms", [])
    check("4. /feed?since=cursor after restart returns 1 atom",
          len(atoms_after_restart) == 1, f"count={len(atoms_after_restart)}")
    if atoms_after_restart:
        restarted_content = atoms_after_restart[0].get("content", "")
        check("4. atom after restart matches atom2", restarted_content == "second atom",
              f"content={restarted_content!r}")

    cursor_after_restart = feed_after_restart.get("cursor", -1)
    check("4. cursor unchanged after restart",
          cursor_after_restart == feed_since.get("cursor", -2),
          f"before={feed_since.get('cursor')} after={cursor_after_restart}")

    stop_relay(proc)

    # ── Step 5: Legacy raw-atom log compatibility ───────────────
    print("\n5. Legacy raw-atom log: relay starts cleanly, new atoms get correct cursors")
    legacy_dir = tempfile.mkdtemp(prefix="punkto_legacy_")
    try:
        os.makedirs(os.path.join(legacy_dir, "data"), exist_ok=True)
        log_path = os.path.join(legacy_dir, "data", "atoms.log.jsonl")
        # Write two legacy raw-atom records (no cursor/log_seq wrapper)
        legacy_atoms = [
            {"punkto": "p:test00000000", "content": "legacy1", "t": int(time.time() * 1000) - 5000},
            {"punkto": "p:test00000000", "content": "legacy2", "t": int(time.time() * 1000) - 4000},
        ]
        with open(log_path, "w") as f:
            for a in legacy_atoms:
                f.write(json.dumps(a) + "\n")

        proc_legacy = start_relay(legacy_dir)
        check("5. Relay with legacy log starts", wait_ready())

        # Verify legacy atoms are in feed
        feed_legacy = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
        check("5. Legacy atoms loaded (feed has >= 2)",
              len(feed_legacy.get("atoms", [])) >= 2,
              f"count={len(feed_legacy.get('atoms', []))}")

        # POST a new atom → should get cursor > 0
        time.sleep(1)
        r_new = requests.post(f"{BASE}/atom", json=make_atom("new after legacy"), timeout=5)
        check("5. New atom accepted after legacy load", r_new.status_code == 201,
              f"status={r_new.status_code}")

        feed_all = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
        check("5. Feed has 3 atoms after new post",
              len(feed_all.get("atoms", [])) >= 3,
              f"count={len(feed_all.get('atoms', []))}")

        cursor_all = feed_all.get("cursor", -1)
        check("5. Cursor after new post > 0", cursor_all > 0, f"cursor={cursor_all}")

        stop_relay(proc_legacy)
    finally:
        shutil.rmtree(legacy_dir, ignore_errors=True)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print("\n" + "=" * 60)
print(f"Results: {PASS}/{PASS + FAIL} passed, {FAIL} failed")
if FAIL == 0:
    print("STATUS: ALL PASS")
else:
    print("STATUS: FAIL")
    sys.exit(1)
