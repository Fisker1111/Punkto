#!/usr/bin/env python3
"""
Point 1 — PUNKTO_REQUIRE_SIG test script

Tests the pure signature functions directly, no HTTP handler instantiation.

Cases:
  A. PUNKTO_REQUIRE_SIG=true  + unsigned atom          => rejected
  B. PUNKTO_REQUIRE_SIG=true  + missing pubkey         => rejected
  C. PUNKTO_REQUIRE_SIG=true  + fake signature         => rejected
  D. PUNKTO_REQUIRE_SIG=true  + valid signed atom      => accepted
  E. PUNKTO_REQUIRE_SIG=true  + modified-after-signing => rejected
  F. PUNKTO_REQUIRE_SIG=false + unsigned atom          => accepted
"""

import os
import sys
import json
import time
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Import pure functions from relay.py
from relay import (
    require_signature_enabled,
    canonical_atom_for_signing,
    verify_atom_signature,
    validate_signature_policy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_atom(**extra):
    """Return a minimal valid atom dict for testing."""
    a = {
        "punkto": "p:test000000a",
        "lat": 1.0,
        "lon": 2.0,
        "t": int(time.time() * 1000),
        "content": "test atom for sig enforcement",
    }
    a.update(extra)
    return a


def sign_atom(atom, private_key):
    """Sign atom per spec: add pubkey first, canonical excludes only sig, then sign."""
    pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    pubkey_b64 = base64.b64encode(pub_bytes).decode()
    # Spec: canonical includes pubkey, excludes only sig
    atom_with_key = {**atom, "pubkey": pubkey_b64}
    canonical = canonical_atom_for_signing(atom_with_key)
    sig = private_key.sign(canonical)
    return base64.b64encode(sig).decode(), pubkey_b64


def assert_rejected(result, label):
    ok, err = result
    if ok:
        print(f"  FAIL {label}: expected rejection, got acceptance")
        return False
    print(f"  PASS {label}: rejected — error={err.get('error')}")
    return True


def assert_accepted(result, label):
    ok, err = result
    if not ok:
        print(f"  FAIL {label}: expected acceptance, got rejection — error={err}")
        return False
    print(f"  PASS {label}: accepted")
    return True


# ---------------------------------------------------------------------------
# Generate keys
# ---------------------------------------------------------------------------

print("=" * 60)
print("PUNKTO_REQUIRE_SIG — signature enforcement tests")
print("=" * 60)

private_key = Ed25519PrivateKey.generate()
private_key2 = Ed25519PrivateKey.generate()  # Different key for fake-sig test

results = []

# ---------------------------------------------------------------------------
# PUNKTO_REQUIRE_SIG=true tests
# ---------------------------------------------------------------------------

os.environ["PUNKTO_REQUIRE_SIG"] = "true"
print(f"\n[PUNKTO_REQUIRE_SIG=true]  require_signature_enabled()={require_signature_enabled()}")

# A. Unsigned atom — no sig, no pubkey
print("\nA. unsigned atom + require_sig=true")
atom_a = make_atom()
results.append(assert_rejected(validate_signature_policy(atom_a), "A"))

# B. Missing pubkey only
print("\nB. missing pubkey + require_sig=true")
atom_b = make_atom(sig=base64.b64encode(b"x" * 64).decode())
results.append(assert_rejected(validate_signature_policy(atom_b), "B"))

# C. Fake signature (valid-format sig from different key)
print("\nC. fake signature + require_sig=true")
atom_c = make_atom()
sig_fake, _ = sign_atom(atom_c, private_key2)  # signed with key2
pub_key1_b64 = base64.b64encode(
    private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
).decode()
atom_c["sig"] = sig_fake
atom_c["pubkey"] = pub_key1_b64  # pubkey1 != key2
results.append(assert_rejected(validate_signature_policy(atom_c), "C"))

# D. Valid signed atom
print("\nD. valid signed atom + require_sig=true")
atom_d = make_atom()
sig_d, pub_d = sign_atom(atom_d, private_key)
atom_d["sig"] = sig_d
atom_d["pubkey"] = pub_d
results.append(assert_accepted(validate_signature_policy(atom_d), "D"))

# E. Modified after signing
print("\nE. modified-after-signing atom + require_sig=true")
atom_e = make_atom()
sig_e, pub_e = sign_atom(atom_e, private_key)
atom_e["sig"] = sig_e
atom_e["pubkey"] = pub_e
atom_e["content"] = "TAMPERED CONTENT"  # modify after signing
results.append(assert_rejected(validate_signature_policy(atom_e), "E"))

# ---------------------------------------------------------------------------
# PUNKTO_REQUIRE_SIG=false tests
# ---------------------------------------------------------------------------

os.environ["PUNKTO_REQUIRE_SIG"] = "false"
print(f"\n[PUNKTO_REQUIRE_SIG=false]  require_signature_enabled()={require_signature_enabled()}")

# F. Unsigned atom allowed
print("\nF. unsigned atom + require_sig=false")
atom_f = make_atom()
results.append(assert_accepted(validate_signature_policy(atom_f), "F"))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(results)
total = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("STATUS: ALL PASS")
else:
    print("STATUS: FAIL")
    sys.exit(1)
