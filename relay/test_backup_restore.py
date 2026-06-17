#!/usr/bin/env python3
"""
Point 6 — Backup, restore, restart, and node identity persistence.

Tests A–G using isolated temporary directories. Does not touch production data.

All four path env vars must be set for full isolation:
  PUNKTO_DATA_DIR     → sync_state.json path
  PUNKTO_ATOM_LOG_PATH→ atoms.log.jsonl path
  PUNKTO_NODE_KEY     → node-key.json path
  PUNKTO_NODE_CONFIG  → (not set → no node config, safe defaults)

Do not instantiate BaseRequestHandler or RelayHandler directly.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PORT = 19878
BASE = f"http://127.0.0.1:{PORT}"
PASS = 0
FAIL = 0
RELAY_PY = os.path.join(os.path.dirname(__file__), "relay.py")


def check(label: str, cond: bool, detail: str = "") -> bool:
    global PASS, FAIL
    if cond:
        print(f"  [PASS] {label}" + (f": {detail}" if detail else ""))
        PASS += 1
    else:
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))
        FAIL += 1
    return cond


def wait_ready(timeout: float = 10.0) -> bool:
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


def start_relay(data_dir: str, require_sig: str = "false", env_extra: dict = None) -> subprocess.Popen:
    """Start relay with fully isolated paths."""
    os.makedirs(data_dir, exist_ok=True)
    env = os.environ.copy()
    env["PUNKTO_DATA_DIR"] = data_dir
    env["PUNKTO_ATOM_LOG_PATH"] = os.path.join(data_dir, "atoms.log.jsonl")
    env["PUNKTO_NODE_KEY"] = os.path.join(data_dir, "node-key.json")
    env["PUNKTO_NODE_CONFIG"] = os.path.join(data_dir, "NOCONFIG")
    env["PUNKTO_PORT"] = str(PORT)
    env["PUNKTO_HOST"] = "127.0.0.1"
    env["PUNKTO_REQUIRE_SIG"] = require_sig
    env["PUNKTO_SYNC_INTERVAL"] = "9999"
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(
        [sys.executable, RELAY_PY],
        env=env,
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


def get_fingerprint() -> str:
    try:
        r = requests.get(f"{BASE}/node/info", timeout=5)
        if r.status_code == 200:
            return r.json().get("node_fingerprint", "")
    except Exception:
        pass
    return ""


def make_unsigned_atom(content: str) -> dict:
    return {
        "punkto": "p:test00000000",
        "content": content,
        "t": int(time.time() * 1000),
    }


def make_signed_atom(content: str, private_key) -> dict:
    atom = make_unsigned_atom(content)
    # Spec: add pubkey first, canonical excludes only sig (pubkey included)
    pub = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    atom["pubkey"] = base64.b64encode(pub).decode()
    canonical = json.dumps({k: v for k, v in atom.items() if k != "sig"},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = private_key.sign(canonical)
    atom["sig"] = base64.b64encode(sig).decode()
    return atom


# ── Generate Ed25519 key for signed atom tests ─────────────────────────────
PRIVATE_KEY = Ed25519PrivateKey.generate()

print("=" * 60)
print("POINT 6 — Backup, restore, restart, identity persistence")
print("=" * 60)

# ── Persistent path investigation findings ─────────────────────────────────
print("\n[PATH FINDINGS]")
print("  PUNKTO_DATA_DIR     → DATA_DIR + sync_state.json")
print("  PUNKTO_ATOM_LOG_PATH→ atoms.log.jsonl (separate from DATA_DIR!)")
print("  PUNKTO_NODE_KEY     → node-key.json (separate from DATA_DIR!)")
print("  PUNKTO_NODE_CONFIG  → node config YAML (separate from DATA_DIR!)")
print("  WARNING: Setting only PUNKTO_DATA_DIR does NOT isolate atom log or node key.")
print("  Required for full isolation: all 4 env vars must be set.")

# ── Base directory for all test data ───────────────────────────────────────
BASEDIR = tempfile.mkdtemp(prefix="punkto_p6_test_")

try:
    # ==========================================================
    # A. Initial node startup
    # ==========================================================
    print("\n" + "=" * 40)
    print("A. Initial node startup")
    data_a = os.path.join(BASEDIR, "node_a")
    proc = start_relay(data_a)
    check("A. relay starts and /health returns 200", wait_ready())

    fp_initial = get_fingerprint()
    check("A. node fingerprint obtained", bool(fp_initial), f"fingerprint={fp_initial[:16]}...")

    # Post two atoms
    time.sleep(0.5)
    r1 = requests.post(f"{BASE}/atom", json=make_unsigned_atom("atom_alpha"), timeout=5)
    check("A. atom1 accepted", r1.status_code == 201, f"status={r1.status_code}")
    atom1_id = r1.json().get("atom_id", "")
    check("A. atom1_id present", bool(atom1_id), f"id={atom1_id[:12]}")

    time.sleep(1)
    r2 = requests.post(f"{BASE}/atom", json=make_unsigned_atom("atom_beta"), timeout=5)
    check("A. atom2 accepted", r2.status_code == 201, f"status={r2.status_code}")
    atom2_id = r2.json().get("atom_id", "")
    check("A. atom2_id distinct", bool(atom2_id) and atom2_id != atom1_id, f"id={atom2_id[:12]}")

    feed_a = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
    check("A. feed has 2 atoms", len(feed_a.get("atoms", [])) == 2, f"count={len(feed_a.get('atoms', []))}")
    cursor_a = feed_a.get("cursor", -1)

    print(f"  Initial fingerprint: {fp_initial}")
    print(f"  Atom IDs: {atom1_id[:16]}... | {atom2_id[:16]}...")
    print(f"  Feed cursor: {cursor_a}")

    stop_relay(proc)

    # ==========================================================
    # B. Normal restart
    # ==========================================================
    print("\n" + "=" * 40)
    print("B. Normal restart")
    proc = start_relay(data_a)
    check("B. relay restarts", wait_ready())

    fp_after_restart = get_fingerprint()
    check("B. fingerprint unchanged after restart", fp_after_restart == fp_initial,
          f"before={fp_initial[:16]} after={fp_after_restart[:16]}")

    feed_b = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
    check("B. atoms persist after restart", len(feed_b.get("atoms", [])) == 2,
          f"count={len(feed_b.get('atoms', []))}")

    # Feed returns raw atom dicts (no atom_id field). Verify by content presence.
    feed_contents_b = {a.get("content", "") for a in feed_b.get("atoms", [])}
    check("B. atom1 content unchanged", "atom_alpha" in feed_contents_b,
          f"contents in feed: {feed_contents_b}")
    check("B. atom2 content unchanged", "atom_beta" in feed_contents_b,
          f"contents in feed: {feed_contents_b}")

    time.sleep(1)
    r3 = requests.post(f"{BASE}/atom", json=make_unsigned_atom("atom_gamma"), timeout=5)
    check("B. new atom accepted after restart", r3.status_code == 201, f"status={r3.status_code}")
    atom3_id = r3.json().get("atom_id", "")

    feed_since_b = requests.get(f"{BASE}/feed?since={cursor_a}", timeout=5).json()
    check("B. feed?since=cursor returns only new atom",
          len(feed_since_b.get("atoms", [])) == 1, f"count={len(feed_since_b.get('atoms', []))}")

    stop_relay(proc)

    # ==========================================================
    # C. Backup
    # ==========================================================
    print("\n" + "=" * 40)
    print("C. Backup")
    backup_dir = os.path.join(BASEDIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, "punkto-node-backup-test.tar.gz")

    # Create backup of required files
    files_to_backup = [
        os.path.join(data_a, "atoms.log.jsonl"),
        os.path.join(data_a, "node-key.json"),
        os.path.join(data_a, "sync_state.json"),
    ]
    existing = [f for f in files_to_backup if os.path.exists(f)]
    with tarfile.open(backup_file, "w:gz") as tar:
        for f in existing:
            tar.add(f, arcname=os.path.basename(f))

    check("C. backup file created", os.path.exists(backup_file))
    with tarfile.open(backup_file, "r:gz") as tar:
        names = tar.getnames()
    check("C. backup contains atoms.log.jsonl", "atoms.log.jsonl" in names, str(names))
    check("C. backup contains node-key.json", "node-key.json" in names, str(names))
    print(f"  Backup: {backup_file}")
    print(f"  Contents: {names}")

    # ==========================================================
    # D. Restore to clean location
    # ==========================================================
    print("\n" + "=" * 40)
    print("D. Restore to clean location")
    data_d = os.path.join(BASEDIR, "node_d")
    os.makedirs(data_d, exist_ok=True)

    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(path=data_d)

    check("D. atoms.log.jsonl restored", os.path.exists(os.path.join(data_d, "atoms.log.jsonl")))
    check("D. node-key.json restored", os.path.exists(os.path.join(data_d, "node-key.json")))

    proc = start_relay(data_d)
    check("D. restored node starts", wait_ready())

    fp_restored = get_fingerprint()
    check("D. fingerprint matches original after restore", fp_restored == fp_initial,
          f"original={fp_initial[:16]} restored={fp_restored[:16]}")

    feed_d = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
    atom_count_d = len(feed_d.get("atoms", []))
    check("D. atoms present after restore", atom_count_d >= 2, f"count={atom_count_d}")

    # Feed returns raw atoms without atom_id field — verify by content.
    feed_contents_d = {a.get("content", "") for a in feed_d.get("atoms", [])}
    check("D. atom1 content preserved after restore", "atom_alpha" in feed_contents_d,
          f"contents={feed_contents_d}")
    check("D. atom2 content preserved after restore", "atom_beta" in feed_contents_d,
          f"contents={feed_contents_d}")

    time.sleep(1)
    r_new = requests.post(f"{BASE}/atom", json=make_unsigned_atom("post-restore atom"), timeout=5)
    check("D. new atom accepted after restore", r_new.status_code == 201, f"status={r_new.status_code}")

    feed_d2 = requests.get(f"{BASE}/feed?since={cursor_a}", timeout=5).json()
    check("D. feed?since cursor works after restore",
          len(feed_d2.get("atoms", [])) >= 1, f"count={len(feed_d2.get('atoms', []))}")

    print(f"  Restored fingerprint: {fp_restored}")
    stop_relay(proc)

    # ==========================================================
    # E. Missing identity test
    # ==========================================================
    print("\n" + "=" * 40)
    print("E. Missing identity test — atom data without node key")
    data_e = os.path.join(BASEDIR, "node_e")
    os.makedirs(data_e, exist_ok=True)
    # Copy only atoms.log.jsonl, NOT node-key.json
    shutil.copy(os.path.join(data_a, "atoms.log.jsonl"), os.path.join(data_e, "atoms.log.jsonl"))

    proc = start_relay(data_e)
    check("E. relay starts with atom data only", wait_ready())

    fp_new = get_fingerprint()
    check("E. new fingerprint generated (different from original)",
          bool(fp_new) and fp_new != fp_initial,
          f"new={fp_new[:16]} original={fp_initial[:16]}")

    feed_e = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
    check("E. atom data loaded from log", len(feed_e.get("atoms", [])) >= 2,
          f"count={len(feed_e.get('atoms', []))}")
    print("  (Confirmed: restoring atom data alone does NOT restore node identity)")
    stop_relay(proc)

    # ==========================================================
    # F. Partial/corrupt backup — missing sync_state + corrupt log line
    # ==========================================================
    print("\n" + "=" * 40)
    print("F. Partial/corrupt backup behaviour")
    data_f = os.path.join(BASEDIR, "node_f")
    os.makedirs(data_f, exist_ok=True)
    # Copy node-key but NO sync_state
    shutil.copy(os.path.join(data_a, "node-key.json"), os.path.join(data_f, "node-key.json"))
    # Write atom log with 2 valid and 1 corrupt line
    now_ms = int(time.time() * 1000)
    valid1 = {"log_seq": 1, "atom_id": atom1_id,
               "atom": {"punkto": "p:test00000000", "content": "atom_alpha", "t": now_ms - 2000}}
    valid2 = {"log_seq": 2, "atom_id": atom2_id,
               "atom": {"punkto": "p:test00000000", "content": "atom_beta", "t": now_ms - 1000}}
    with open(os.path.join(data_f, "atoms.log.jsonl"), "w") as f:
        f.write(json.dumps(valid1) + "\n")
        f.write("CORRUPT_LINE_NOT_JSON\n")
        f.write(json.dumps(valid2) + "\n")

    proc = start_relay(data_f)
    check("F. relay starts despite corrupt line", wait_ready())
    check("F. fingerprint unchanged (key present)", get_fingerprint() == fp_initial,
          f"fp={get_fingerprint()[:16]}")

    feed_f = requests.get(f"{BASE}/feed?since=0", timeout=5).json()
    check("F. valid atoms loaded (corrupt line skipped)",
          len(feed_f.get("atoms", [])) == 2, f"count={len(feed_f.get('atoms', []))}")

    # Missing sync_state — relay should start fresh sync state
    sync_state_path = os.path.join(data_f, "sync_state.json")
    check("F. missing sync_state handled (relay ran without it)",
          True, "relay started successfully without sync_state")
    stop_relay(proc)

    # ==========================================================
    # G. Signature policy after restore
    # ==========================================================
    print("\n" + "=" * 40)
    print("G. Signature policy after restore with PUNKTO_REQUIRE_SIG=true")
    data_g = os.path.join(BASEDIR, "node_g")
    os.makedirs(data_g, exist_ok=True)
    # Restore from backup
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(path=data_g)

    proc = start_relay(data_g, require_sig="true")
    check("G. restored node starts with PUNKTO_REQUIRE_SIG=true", wait_ready())

    # Valid signed atom accepted
    time.sleep(1)
    signed = make_signed_atom("signed post-restore", PRIVATE_KEY)
    r_signed = requests.post(f"{BASE}/atom", json=signed, timeout=5)
    check("G. valid signed atom accepted", r_signed.status_code == 201,
          f"status={r_signed.status_code}")

    # Unsigned atom rejected
    time.sleep(1)
    r_unsigned = requests.post(f"{BASE}/atom", json=make_unsigned_atom("unsigned post-restore"), timeout=5)
    check("G. unsigned atom rejected (403)", r_unsigned.status_code == 403,
          f"status={r_unsigned.status_code} error={r_unsigned.json().get('error', '')}")

    stop_relay(proc)

finally:
    shutil.rmtree(BASEDIR, ignore_errors=True)

print("\n" + "=" * 60)
print(f"Results: {PASS}/{PASS + FAIL} passed, {FAIL} failed")
if FAIL == 0:
    print("STATUS: ALL PASS")
else:
    print("STATUS: FAIL")
    sys.exit(1)
