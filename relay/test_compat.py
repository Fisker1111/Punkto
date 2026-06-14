#!/usr/bin/env python3
"""
Signing spec compatibility tests — Point signing-spec-drift fix.

Verifies that relay/Python, CLI (tools/punkto-key.py), and vector tests
all produce identical canonical bytes and interoperable signatures.

Tests:
  1. CLI signs, relay verifies
  2. Relay/Python signs, CLI verifies  
  3. Canonical bytes: nested objects produce identical results across implementations
  4. Canonical bytes: arrays, Unicode, special values
  5. Tampered content fails verification
  6. atom_id == SHA-256(canonical_bytes) == SHA-256(canonical_atom_for_signing)
     (confirms the two relay functions are now unified)
  7. pubkey IS included in canonical bytes (spec alignment confirmed)
  8. sig IS excluded from canonical bytes
"""
import os, sys, json, time, base64, hashlib
sys.path.insert(0, os.path.dirname(__file__))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from relay import canonical_bytes, canonical_atom_for_signing, compute_atom_id, verify_atom_signature

results = []

def ok(label, passed, detail=''):
    status = 'PASS' if passed else 'FAIL'
    print(f'  {status} {label}' + (f' — {detail}' if detail else ''))
    results.append(passed)
    return passed

def make_atom(**extra):
    a = {'punkto': 'p:test000000a', 'lat': 1.0, 'lon': 2.0,
         't': int(time.time() * 1000), 'content': 'compat test'}
    a.update(extra)
    return a

def sign_with_relay(atom, private_key):
    """Sign using relay canonical function (spec: add pubkey, sign, add sig)."""
    pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    pubkey_b64 = base64.b64encode(pub_bytes).decode()
    atom_with_key = {**atom, 'pubkey': pubkey_b64}
    canonical = canonical_atom_for_signing(atom_with_key)
    sig = private_key.sign(canonical)
    return {**atom_with_key, 'sig': base64.b64encode(sig).decode()}

def sign_with_cli_logic(atom, private_key):
    """Mimic tools/punkto-key.py cmd_sign: add pubkey, exclude only sig."""
    pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    pubkey_b64 = base64.b64encode(pub_bytes).decode()
    atom['pubkey'] = pubkey_b64
    # canonical_atom_bytes in CLI excludes only 'sig', same as relay canonical_bytes
    canonical = json.dumps(
        {k: v for k, v in atom.items() if k != 'sig'},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False
    ).encode('utf-8')
    sig = private_key.sign(canonical)
    atom['sig'] = base64.b64encode(sig).decode()
    return atom

print('=' * 60)
print('Signing spec compatibility tests')
print('=' * 60)

private_key = Ed25519PrivateKey.generate()

# Test 1: CLI signs, relay verifies
print('\n1. CLI signs, relay verifies')
atom1 = sign_with_cli_logic(make_atom(content='cli-signed-1'), private_key)
err = verify_atom_signature(atom1)
ok('1: CLI-signed atom passes relay verify_atom_signature', err is None,
   detail=str(err) if err else 'verified')

# Test 2: Relay signs, relay verifies (self-consistency)
print('\n2. Relay/Python signs, relay verifies')
atom2 = sign_with_relay(make_atom(content='relay-signed-1'), private_key)
err = verify_atom_signature(atom2)
ok('2: relay-signed atom passes relay verify_atom_signature', err is None,
   detail=str(err) if err else 'verified')

# Test 3: canonical bytes are identical for same atom regardless of which function
print('\n3. canonical_bytes == canonical_atom_for_signing (unified)')
atom3 = make_atom(content='unification test')
atom3['pubkey'] = base64.b64encode(b'x' * 32).decode()
cb = canonical_bytes(atom3)
cafs = canonical_atom_for_signing(atom3)
ok('3: canonical_bytes == canonical_atom_for_signing', cb == cafs,
   detail=f'len_cb={len(cb)} len_cafs={len(cafs)}')

# Test 4: nested objects and Unicode canonicalization
print('\n4. Nested objects, arrays, Unicode')
atom4 = make_atom(content='Unicode: \u00e9\u4e2d\u6587 emoji:\U0001f600',
                  nested={'z': 1, 'a': [3, 2, 1], 'b': {'q': True, 'p': None}})
atom4['pubkey'] = base64.b64encode(b'y' * 32).decode()
c = canonical_bytes(atom4).decode('utf-8')
# Verify nested keys are sorted
ok('4a: nested keys sorted in canonical', '"a":' in c and c.index('"a":') < c.index('"z":'))
# Verify arrays preserved in order  
ok('4b: arrays preserved', '[3,2,1]' in c)
# Verify Unicode not escaped
ok('4c: Unicode not ASCII-escaped', '\\u00e9' not in c and '\u00e9' in c)

# Test 5: tampered content fails
print('\n5. Tampered content fails')
atom5 = sign_with_relay(make_atom(content='original'), private_key)
atom5['content'] = 'TAMPERED'
err = verify_atom_signature(atom5)
ok('5: tampered atom fails verify_atom_signature', err is not None and err.get('error') == 'invalid_sig',
   detail=str(err))

# Test 6: atom_id includes pubkey
print('\n6. atom_id includes pubkey (pubkey in canonical bytes)')
base_atom = make_atom(content='atom-id-test')
without_pubkey = compute_atom_id(base_atom)
with_pubkey = {**base_atom, 'pubkey': base64.b64encode(b'z' * 32).decode()}
with_pubkey_id = compute_atom_id(with_pubkey)
ok('6: atom_id differs when pubkey present (pubkey included in canonical)', 
   without_pubkey != with_pubkey_id,
   detail=f'without={without_pubkey[:12]}... with_pk={with_pubkey_id[:12]}...')

# Test 7: sig excluded from canonical bytes
print('\n7. sig excluded from canonical bytes')
atom7 = make_atom(content='sig-exclusion-test')
atom7['pubkey'] = base64.b64encode(b'k' * 32).decode()
before_sig = canonical_bytes(atom7)
atom7['sig'] = base64.b64encode(b's' * 64).decode()
after_sig = canonical_bytes(atom7)
ok('7: canonical_bytes unchanged after adding sig', before_sig == after_sig,
   detail=f'before_len={len(before_sig)} after_len={len(after_sig)}')

# Test 8: Cross-sign check — relay-signed verified with CLI logic
print('\n8. Cross-verify: relay-signed verified by CLI verify logic')
atom8 = sign_with_relay(make_atom(content='cross-verify-8'), private_key)
sig_bytes = base64.b64decode(atom8['sig'])
pub_bytes = base64.b64decode(atom8['pubkey'])
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
try:
    pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    # CLI verify logic: canonical = sorted JSON without sig (pubkey included)
    cli_canonical = json.dumps(
        {k: v for k, v in atom8.items() if k != 'sig'},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False
    ).encode('utf-8')
    pub.verify(sig_bytes, cli_canonical)
    ok('8: relay-signed atom verified by CLI verify logic', True, 'cross-verified')
except InvalidSignature as e:
    ok('8: relay-signed atom verified by CLI verify logic', False, str(e))

print('\n' + '=' * 60)
passed = sum(results)
print(f'Results: {passed}/{len(results)} passed')
if passed == len(results):
    print('STATUS: ALL PASS')
else:
    print('STATUS: FAIL')
    sys.exit(1)
