#!/usr/bin/env python3
"""Smoke tests for punkto-relay v0.1.

Usage:
    python3 test_relay.py

Starts a relay on 127.0.0.1:18000 in a background thread, exercises every
endpoint, and verifies buffer rotation. Cleans up its own data dir.
Works with or without pytest installed.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
from typing import Any, Dict


TEST_HOST = "127.0.0.1"
TEST_PORT = 18000
BASE_URL = f"http://{TEST_HOST}:{TEST_PORT}"


# Configure relay env BEFORE importing the module so its module-level config picks it up.
_TMPDIR = tempfile.mkdtemp(prefix="punkto-relay-test-")
os.environ["PUNKTO_HOST"] = TEST_HOST
os.environ["PUNKTO_PORT"] = str(TEST_PORT)
os.environ["PUNKTO_DATA_DIR"] = _TMPDIR
os.environ["PUNKTO_NODE_NAME"] = "relay-test"
os.environ["PUNKTO_PEERS"] = ""  # no peers
os.environ["PUNKTO_BUFFER_ATOMS"] = "5"
os.environ["PUNKTO_BUFFER_HOURS"] = "168"
os.environ["PUNKTO_LATEST_LIMIT"] = "10"
os.environ["PUNKTO_SYNC_INTERVAL"] = "3600"  # effectively disabled
os.environ["PUNKTO_NODE_CONFIG"] = os.path.join(_TMPDIR, "punkto-node.yml")
os.environ["PUNKTO_NODE_KEY"] = os.path.join(_TMPDIR, "node-key.json")
os.environ["PUNKTO_TEST_SECRET"] = "relay-test-env-secret-value"
with open(os.environ["PUNKTO_NODE_CONFIG"], "w", encoding="utf-8") as f:
    f.write("""core:
  node_name: Public Test Node
  public_url: https://relay.test.example
  domain_dns: relay.test.example
  hostnames:
    - relay-test
    - www
roles:
  web: true
  relay: true
  db_sharing: false
network:
  seed_nodes:
    - https://seed1.example
    - https://seed2.example
  known_nodes:
    - https://known.example
operator:
  private_key: should-never-leak
  token: hidden-token
storage:
  path: /data/private-ish
serving:
  serve_recent: true
  serve_pinned: true
  serve_archive: false
""")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

import relay  # noqa: E402


_server = None
_server_thread: threading.Thread | None = None


def _start_server() -> None:
    global _server, _server_thread
    server, _, _ = relay.build_server(host=TEST_HOST, port=TEST_PORT)
    _server = server
    _server_thread = threading.Thread(target=server.serve_forever, daemon=True, name="relay-test")
    _server_thread.start()
    # wait for server to be ready
    for _ in range(40):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=1)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.05)
    raise RuntimeError("relay test server did not come up")


def _stop_server() -> None:
    if _server is not None:
        _server.shutdown()
        _server.server_close()
    shutil.rmtree(_TMPDIR, ignore_errors=True)


def _atom(punkto: str = "p:u07qsuustfsh", t: int | None = None, **extra: Any) -> Dict[str, Any]:
    if t is None:
        t = relay._now_ms()
    a = {"punkto": punkto, "t": t}
    a.update(extra)
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health() -> None:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["node"] == "relay-test"
    assert isinstance(body["buffer_size"], int)


def test_info() -> None:
    r = requests.get(f"{BASE_URL}/info", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["node"] == "relay-test"
    assert body["version"] == relay.VERSION
    assert body["buffer_atoms_max"] == 5
    assert body["buffer_hours_max"] == 168
    assert body["peers"] == []
    assert isinstance(body["buffer_size"], int)


def _flatten_json_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        strings: list[str] = []
        for key, child in value.items():
            strings.append(str(key))
            strings.extend(_flatten_json_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(_flatten_json_strings(child))
        return strings
    if value is None:
        return []
    return [str(value)]


def test_node_info_public_status_shape() -> None:
    r = requests.get(f"{BASE_URL}/node/info", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["software"] == {"name": "Punkto", "version": relay.VERSION, "runtime": "relay"}
    assert body["node"]["name"] == "Public Test Node"
    assert body["node"]["public_url"] == "https://relay.test.example"
    assert body["node"]["domain_dns"] == "relay.test.example"
    assert body["node"]["hostnames"] == ["relay-test", "www"]
    assert body["node"]["fingerprint"].startswith("node:")
    assert body["node"]["key_alg"] == "sha256-secret-v1"
    assert body["node"]["identity_loaded"] is True
    assert isinstance(body["node"]["identity_created_at"], str)
    assert body["roles"] == {"web": True, "relay": True, "db_sharing": False}
    assert body["serving"] == {"serve_recent": True, "serve_pinned": True, "serve_archive": False}
    assert body["network"]["seed_nodes"] == ["https://seed1.example", "https://seed2.example"]
    assert "https://known.example" in body["network"]["known_nodes"]
    assert body["config"] == {"loaded": True, "path": "/config/punkto-node.yml"}
    assert body["health"]["status"] == "ok"


def test_node_info_stats_fields_exist() -> None:
    r = requests.get(f"{BASE_URL}/node/info", timeout=5)
    assert r.status_code == 200, r.text
    stats = r.json()["stats"]
    assert isinstance(stats["buffer_size"], int)
    assert "oldest_t" in stats
    assert "newest_t" in stats


def test_node_info_does_not_expose_private_values() -> None:
    r = requests.get(f"{BASE_URL}/node/info", timeout=5)
    assert r.status_code == 200, r.text
    text = r.text
    flattened = "\n".join(_flatten_json_strings(r.json()))
    forbidden = [
        "private_key",
        "should-never-leak",
        "hidden-token",
        "relay-test-env-secret-value",
        "PUNKTO_TEST_SECRET",
        "/data/private-ish",
    ]
    for needle in forbidden:
        assert needle not in text
        assert needle not in flattened


def test_load_or_create_node_identity_roundtrip() -> None:
    tmpdir = tempfile.mkdtemp(prefix="punkto-node-identity-")
    try:
        key_path = os.path.join(tmpdir, "node-key.json")
        first, loaded1, used1, created1 = relay.load_or_create_node_identity(key_path)
        second, loaded2, used2, created2 = relay.load_or_create_node_identity(key_path)
        assert loaded1 is True and loaded2 is True
        assert created1 is True and created2 is False
        assert used1 == key_path and used2 == key_path
        assert first["fingerprint"] == second["fingerprint"]
        assert first["public_key"] == second["public_key"]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_load_or_create_node_identity_invalid_fails() -> None:
    tmpdir = tempfile.mkdtemp(prefix="punkto-node-identity-invalid-")
    try:
        key_path = os.path.join(tmpdir, "node-key.json")
        with open(key_path, "w", encoding="utf-8") as f:
            f.write('{"version":1,"key_alg":"sha256-secret-v1","created_at":"x","public_key":"p","private_key":"q","fingerprint":"node:deadbeefcafe"}')
        try:
            relay.load_or_create_node_identity(key_path)
            raise AssertionError("expected SystemExit for invalid identity file")
        except SystemExit as exc:
            assert exc.code == 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_post_valid_atom() -> None:
    a = _atom(f="alice", x="hello world")
    r = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "accepted"
    assert body["atom_id"] == relay.compute_atom_id(a)
    assert body["punkto"] == a["punkto"]


def test_post_duplicate_atom() -> None:
    a = _atom(t=relay._now_ms() - 1000, f="bob", x="dup test")
    first = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
    assert first.status_code == 201, first.text
    aid = first.json()["atom_id"]
    second = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["status"] == "duplicate"
    assert body["atom_id"] == aid


def test_post_invalid_missing_punkto() -> None:
    r = requests.post(f"{BASE_URL}/atom", json={"t": relay._now_ms()}, timeout=5)
    assert r.status_code in (400, 422), r.text
    body = r.json()
    assert body["error"] == "invalid_punkto"


def test_post_invalid_punkto_format() -> None:
    r = requests.post(f"{BASE_URL}/atom", json={"punkto": "nope", "t": relay._now_ms()}, timeout=5)
    assert r.status_code in (400, 422), r.text
    body = r.json()
    assert body["error"] == "invalid_punkto"


def test_post_invalid_timestamp() -> None:
    r = requests.post(f"{BASE_URL}/atom", json={"punkto": "p:u07qsuustfsh", "t": "now"}, timeout=5)
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"] == "invalid_timestamp"


def test_post_no_f_no_x_accepted() -> None:
    """Per v0.1: only punkto and t are required. f and x are optional."""
    a = _atom(t=relay._now_ms() - 2000, punkto="p:u07qskyuhbus")
    r = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "accepted"


def test_latest() -> None:
    r = requests.get(f"{BASE_URL}/latest", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["atoms"], list)
    assert len(body["atoms"]) > 0
    assert body["node"] == "relay-test"
    assert isinstance(body["served_at"], int)
    assert isinstance(body["buffer_size"], int)
    # Sorted newest first by t
    ts = [int(a["t"]) for a in body["atoms"]]
    assert ts == sorted(ts, reverse=True), f"atoms not sorted desc by t: {ts}"


def test_feed_initial() -> None:
    r = requests.get(f"{BASE_URL}/feed", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["atoms"], list)
    assert isinstance(body["cursor"], int)


def test_buffer_rotation() -> None:
    """Post atoms beyond PUNKTO_BUFFER_ATOMS=5; verify oldest are pruned."""
    # Use unique punktos and timestamps so atom_ids are distinct.
    base_t = relay._now_ms() - 10_000
    canonical_pool = [
        "p:u07qsuustfsh",
        "p:u07qskyuhbus",
        "p:u07qjn4k2sus",
        "p:u07qjh7k02zy",
        "p:u07qsvy8txhf",
        "p:u07qskyuhbmw",
        "p:u07qskyuhbuu",
        "p:u07qskyuhsqu",
        "p:u07quvubhgbd",
        "p:u07qskyuhbmy",
    ]
    for i, p in enumerate(canonical_pool):
        a = _atom(punkto=p, t=base_t + i * 100, f="rot", x=f"rotation-{i}")
        r = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
        assert r.status_code in (200, 201), r.text

    # Buffer must not exceed max_atoms=5
    info = requests.get(f"{BASE_URL}/info", timeout=5).json()
    assert info["buffer_size"] <= 5, f"buffer_size {info['buffer_size']} > 5"

    # Latest should reflect the most recent atoms (text contains 'rotation-N' for highest N)
    latest = requests.get(f"{BASE_URL}/latest", timeout=5).json()
    assert len(latest["atoms"]) <= 5
    texts = [str(a.get("x", "")) for a in latest["atoms"]]
    # Newest few rotation-N entries should be present; rotation-0 should be gone.
    assert any("rotation-9" in t for t in texts), f"latest does not contain newest atom: {texts}"
    assert not any(t == "rotation-0" for t in texts), f"oldest atom not pruned: {texts}"


def test_p_atom_id_known() -> None:
    a = _atom(punkto="p:u07qsuustfsh", t=relay._now_ms() - 500, f="og", x="og card test")
    r = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
    assert r.status_code in (200, 201)
    aid = r.json()["atom_id"]
    page = requests.get(f"{BASE_URL}/p/{aid}", timeout=5)
    assert page.status_code == 200
    html = page.text
    assert "og:title" in html
    assert "twitter:card" in html
    assert aid in html or "og card test" in html


def test_p_atom_id_unknown() -> None:
    bogus = "0" * 64
    page = requests.get(f"{BASE_URL}/p/{bogus}", timeout=5)
    assert page.status_code == 200
    assert "Punkto" in page.text


def test_p_canonical_bare() -> None:
    """`/p/<spatial>` (no `p:` prefix) renders the most recent atom at that location."""
    canonical = "p:u07qjn4k2sus"
    bare = canonical[2:]
    a_old = _atom(punkto=canonical, t=relay._now_ms() - 5000, f="old", x="older message")
    a_new = _atom(punkto=canonical, t=relay._now_ms() - 100, f="new", x="newest at this place")
    for a in (a_old, a_new):
        r = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
        assert r.status_code in (200, 201)
    page = requests.get(f"{BASE_URL}/p/{bare}", timeout=5)
    assert page.status_code == 200
    html = page.text
    assert "og:title" in html
    assert "twitter:card" in html
    assert canonical in html  # canonical form rendered in body
    assert "newest at this place" in html  # latest atom selected
    assert "older message" not in html  # older atom not shown


def test_p_canonical_with_prefix() -> None:
    """`/p/p:<spatial>` (with literal `p:` prefix) also works."""
    canonical = "p:u07qjh7k02zy"
    a = _atom(punkto=canonical, t=relay._now_ms() - 200, f="prefixed", x="with prefix link")
    r = requests.post(f"{BASE_URL}/atom", json=a, timeout=5)
    assert r.status_code in (200, 201)
    page = requests.get(f"{BASE_URL}/p/{canonical}", timeout=5)
    assert page.status_code == 200
    html = page.text
    assert "og:title" in html
    assert canonical in html
    assert "with prefix link" in html


def test_p_canonical_unknown() -> None:
    """Valid canonical form with no atoms in buffer renders the no-atoms fallback."""
    page = requests.get(f"{BASE_URL}/p/u07q000000zz", timeout=5)
    assert page.status_code == 200
    assert "Punkto" in page.text


def test_options_cors() -> None:
    r = requests.options(f"{BASE_URL}/atom", timeout=5)
    assert r.status_code == 204
    assert r.headers.get("Access-Control-Allow-Origin") == "*"


ALL_TESTS = [
    test_health,
    test_info,
    test_node_info_public_status_shape,
    test_node_info_stats_fields_exist,
    test_node_info_does_not_expose_private_values,
    test_load_or_create_node_identity_roundtrip,
    test_load_or_create_node_identity_invalid_fails,
    test_post_valid_atom,
    test_post_duplicate_atom,
    test_post_invalid_missing_punkto,
    test_post_invalid_punkto_format,
    test_post_invalid_timestamp,
    test_post_no_f_no_x_accepted,
    test_latest,
    test_feed_initial,
    test_buffer_rotation,
    test_p_atom_id_known,
    test_p_atom_id_unknown,
    test_p_canonical_bare,
    test_p_canonical_with_prefix,
    test_p_canonical_unknown,
    test_options_cors,
]


def main() -> int:
    _start_server()
    failures = 0
    try:
        for fn in ALL_TESTS:
            name = fn.__name__
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}: {e}")
                traceback.print_exc()
            except Exception as e:
                failures += 1
                print(f"  ERROR {name}: {e}")
                traceback.print_exc()
    finally:
        _stop_server()
    total = len(ALL_TESTS)
    if failures == 0:
        print(f"\n  {total}/{total} tests passed")
        return 0
    print(f"\n  {total - failures}/{total} tests passed, {failures} failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
