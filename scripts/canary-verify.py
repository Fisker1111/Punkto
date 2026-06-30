#!/usr/bin/env python3
"""Canary deploy verification: unsigned rejection + signed acceptance."""
import json, time, base64, urllib.request, urllib.error, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

BASE = "https://node2.punkto.xyz"
PUNKTO = "p:u07qsuseqxnv-05sn2j"

# --- Test 1: Unsigned atom (expect 403) ---
print("=== UNSIGNED ATOM TEST (expect 403) ===")
atom_unsigned = {
    "punkto": PUNKTO,
    "lat": 55.6761,
    "lon": 12.5683,
    "t": int(time.time() * 1000),
    "content": "unsigned canary test",
}
req = urllib.request.Request(
    f"{BASE}/atom",
    data=json.dumps(atom_unsigned).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    resp = urllib.request.urlopen(req)
    print(f"HTTP {resp.status}")
    print(resp.read().decode())
    print("FAIL: unsigned atom was accepted")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
    body = e.read().decode()
    print(body)
    if e.code == 403:
        print("PASS: unsigned atom rejected with 403")
    else:
        print(f"FAIL: expected 403, got {e.code}")

# --- Test 2: Signed atom (expect 201) ---
print()
print("=== SIGNED ATOM TEST (expect 201) ===")
priv = Ed25519PrivateKey.generate()
pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
atom_signed = {
    "punkto": PUNKTO,
    "lat": 55.6761,
    "lon": 12.5683,
    "t": int(time.time() * 1000),
    "content": "Canary deploy signed atom test node2",
    "pubkey": base64.b64encode(pub).decode(),
}
canonical = json.dumps(atom_signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
sig = priv.sign(canonical)
atom_signed["sig"] = base64.b64encode(sig).decode()

req = urllib.request.Request(
    f"{BASE}/atom",
    data=json.dumps(atom_signed).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    resp = urllib.request.urlopen(req)
    print(f"HTTP {resp.status}")
    print(resp.read().decode())
    if resp.status == 201:
        print("PASS: signed atom accepted with 201")
    else:
        print(f"FAIL: expected 201, got {resp.status}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
    print(e.read().decode())
    print("FAIL: signed atom was rejected")

# --- Test 3: Feed check ---
print()
print("=== FEED CHECK ===")
time.sleep(1)
req = urllib.request.Request(f"{BASE}/feed")
resp = urllib.request.urlopen(req)
feed = json.loads(resp.read().decode())
atoms = feed.get("atoms", [])
print(f"feed count: {len(atoms)}")
for a in atoms[:5]:
    print(f"  atom: punkto={a.get('punkto')}, sig={'yes' if a.get('sig') else 'no'}")

print()
print("=== DONE ===")
