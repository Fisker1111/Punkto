#!/usr/bin/env python3
"""punkto-key — generate, import, sign, verify Punkto identities.

A single-file script. Run on any device with Python 3.8+ and `cryptography`.

  pip install cryptography
  python3 punkto-key.py new                    # mint new identity (12-word phrase)
  python3 punkto-key.py import <12 words ...>  # restore identity from phrase
  python3 punkto-key.py sign  <atom.json>      # sign a Punkto atom (reads private key)
  python3 punkto-key.py verify <atom.json>     # verify signature on a Punkto atom

Produces an Ed25519 keypair derived deterministically from a BIP39 mnemonic.
The mnemonic is the ONLY secret. Store on paper, in a password manager, or in
encrypted cold storage. The public key and author_id are safe to share.

Format is canonical and reproducible across implementations:
  - 128-bit entropy + 4-bit SHA-256 checksum -> 12 BIP39 words
  - PBKDF2-HMAC-SHA512(mnemonic, "mnemonic", 2048 iters) -> 64-byte seed
  - First 32 bytes -> Ed25519 private key seed
  - author_id = base32_geohash(SHA-256(pubkey))[:12]

See ../punkto.identity.md (when written) for the full spec.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
import urllib.request
from pathlib import Path
from typing import List, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
except ImportError:
    sys.stderr.write(
        "This script needs `cryptography`:  pip install cryptography\n"
    )
    sys.exit(1)

# Punkto canonical Base32 alphabet (same as geohash3d / Punkti)
GEOHASH_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"

# BIP39 English wordlist (cached locally on first use)
BIP39_URL = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"
BIP39_CACHE = Path.home() / ".cache" / "punkto-bip39-english.txt"


def load_wordlist() -> List[str]:
    if BIP39_CACHE.exists():
        words = BIP39_CACHE.read_text().split()
    else:
        sys.stderr.write(f"fetching BIP39 wordlist (one-time) -> {BIP39_CACHE} ... ")
        with urllib.request.urlopen(BIP39_URL, timeout=15) as r:
            data = r.read().decode("utf-8")
        BIP39_CACHE.parent.mkdir(parents=True, exist_ok=True)
        BIP39_CACHE.write_text(data)
        words = data.split()
        sys.stderr.write("done.\n")
    if len(words) != 2048:
        raise RuntimeError(f"wordlist has {len(words)} words, expected 2048")
    return words


def entropy_to_mnemonic(entropy: bytes, words: List[str]) -> List[str]:
    if len(entropy) != 16:
        raise ValueError("need 128 bits (16 bytes) of entropy for 12 words")
    checksum = hashlib.sha256(entropy).digest()[0] >> 4  # top 4 bits
    bits = int.from_bytes(entropy, "big") << 4 | checksum
    return [words[(bits >> (11 * (11 - i))) & 0x7FF] for i in range(12)]


def mnemonic_to_entropy(mnemonic: List[str], words: List[str]) -> bytes:
    if len(mnemonic) != 12:
        raise ValueError(f"need exactly 12 words, got {len(mnemonic)}")
    bits = 0
    for w in mnemonic:
        try:
            idx = words.index(w)
        except ValueError:
            raise ValueError(f"word not in BIP39 list: {w!r}")
        bits = (bits << 11) | idx
    checksum = bits & 0xF
    entropy = (bits >> 4).to_bytes(16, "big")
    expected = hashlib.sha256(entropy).digest()[0] >> 4
    if checksum != expected:
        raise ValueError("mnemonic checksum invalid (typo in your phrase?)")
    return entropy


def mnemonic_to_seed(mnemonic: List[str], passphrase: str = "") -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha512",
        " ".join(mnemonic).encode("utf-8"),
        ("mnemonic" + passphrase).encode("utf-8"),
        2048,
        dklen=64,
    )


def seed_to_keypair(seed: bytes) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    priv = Ed25519PrivateKey.from_private_bytes(seed[:32])
    return priv, priv.public_key()


def pubkey_bytes(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def base32_geohash(data: bytes) -> str:
    """Encode bytes using Punkto's geohash alphabet (5 bits per char)."""
    bits = int.from_bytes(data, "big")
    nbits = len(data) * 8
    nchars = (nbits + 4) // 5
    out = []
    for i in range(nchars):
        shift = nbits - (i + 1) * 5
        if shift < 0:
            chunk = (bits << -shift) & 0x1F
        else:
            chunk = (bits >> shift) & 0x1F
        out.append(GEOHASH_ALPHABET[chunk])
    return "".join(out)


def author_id(pub: Ed25519PublicKey) -> str:
    digest = hashlib.sha256(pubkey_bytes(pub)).digest()
    return base32_geohash(digest)[:12]


def pub_b64(pub: Ed25519PublicKey) -> str:
    import base64
    return base64.b64encode(pubkey_bytes(pub)).decode("ascii")


def sig_b64(priv: Ed25519PrivateKey, msg: bytes) -> str:
    import base64
    return base64.b64encode(priv.sign(msg)).decode("ascii")


def canonical_atom_bytes(atom: dict) -> bytes:
    """Canonical JSON for atom_id and signing: sorted keys, no whitespace,
    UTF-8, sig field excluded."""
    clean = {k: v for k, v in atom.items() if k != "sig"}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_atom_id(atom: dict) -> str:
    return hashlib.sha256(canonical_atom_bytes(atom)).hexdigest()


# --- commands ---------------------------------------------------------------

def cmd_new() -> None:
    words = load_wordlist()
    entropy = secrets.token_bytes(16)
    mnemonic = entropy_to_mnemonic(entropy, words)
    seed = mnemonic_to_seed(mnemonic)
    priv, pub = seed_to_keypair(seed)

    aid = author_id(pub)
    pubkey = pub_b64(pub)

    print("┌─────────────────────────────────────────────────────────────────┐")
    print("│  PUNKTO IDENTITY — KEEP SAFE, STORE OFFLINE                     │")
    print("├─────────────────────────────────────────────────────────────────┤")
    print(f"│  Author ID:  {aid:<52} │")
    print(f"│  Pubkey:     {pubkey:<52} │")
    print("│                                                                 │")
    print("│  Recovery phrase (12 words) — anyone with this IS you:          │")
    cols = 3
    rows = (len(mnemonic) + cols - 1) // cols
    for r in range(rows):
        line = "│   "
        for c in range(cols):
            idx = r + c * rows
            if idx < len(mnemonic):
                line += f"{idx+1:>2}. {mnemonic[idx]:<10}  "
        line = line.ljust(66) + " │"
        print(line)
    print("└─────────────────────────────────────────────────────────────────┘")
    print()
    print("Next steps:")
    print("  1. WRITE DOWN the 12 words on paper. This is your only backup.")
    print("  2. Optionally save the JSON below to encrypted cold storage.")
    print("  3. The Pubkey + Author ID are safe to share.")
    print()
    print("JSON for import to PWA / cold storage:")
    print(json.dumps({
        "version": "punkto-identity-v0.1",
        "author_id": aid,
        "pubkey": pubkey,
        "mnemonic": mnemonic,
    }, indent=2))


def cmd_import(args: List[str]) -> None:
    if len(args) != 12:
        sys.exit("need exactly 12 words: punkto-key.py import w1 w2 ... w12")
    words = load_wordlist()
    mnemonic = [w.strip().lower() for w in args]
    entropy = mnemonic_to_entropy(mnemonic, words)  # raises if invalid
    seed = mnemonic_to_seed(mnemonic)
    priv, pub = seed_to_keypair(seed)
    aid = author_id(pub)
    print(json.dumps({
        "version": "punkto-identity-v0.1",
        "author_id": aid,
        "pubkey": pub_b64(pub),
        "mnemonic": mnemonic,
        "entropy_hex": entropy.hex(),
    }, indent=2))


def _load_priv_from_env_or_prompt() -> Ed25519PrivateKey:
    env = os.environ.get("PUNKTO_MNEMONIC")
    if env:
        mnemonic = env.split()
    else:
        try:
            line = input("enter 12-word mnemonic: ").strip()
        except EOFError:
            sys.exit("no mnemonic provided")
        mnemonic = line.split()
    words = load_wordlist()
    mnemonic_to_entropy(mnemonic, words)  # validate
    seed = mnemonic_to_seed(mnemonic)
    priv, _ = seed_to_keypair(seed)
    return priv


def cmd_sign(path: str) -> None:
    atom = json.loads(Path(path).read_text())
    priv = _load_priv_from_env_or_prompt()
    import base64 as _b64
    pub_raw = pubkey_bytes(priv.public_key())
    pubkey_b64 = _b64.b64encode(pub_raw).decode("ascii")
    # Spec: add pubkey to atom BEFORE computing canonical bytes
    # canonical = sorted JSON without sig (pubkey IS included)
    atom["pubkey"] = pubkey_b64
    msg = canonical_atom_bytes(atom)  # excludes only sig
    atom["sig"] = sig_b64(priv, msg)
    print(json.dumps(atom, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def cmd_verify(path: str) -> None:
    import base64
    atom = json.loads(Path(path).read_text())
    sig = atom.get("sig")
    pub_b = atom.get("pubkey") or atom.get("pk")
    if not sig or not pub_b:
        sys.exit("atom needs both 'sig' and 'pubkey' fields to verify")
    pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b))
    msg = canonical_atom_bytes(atom)
    try:
        pub.verify(base64.b64decode(sig), msg)
        print("OK — signature valid")
        print(f"atom_id: {compute_atom_id(atom)}")
    except InvalidSignature:
        sys.exit("INVALID — signature does not match")


USAGE = """\
usage:
  punkto-key.py new                          mint a fresh identity
  punkto-key.py import w1 w2 ... w12         restore from 12-word phrase
  punkto-key.py sign <atom.json>             sign an atom (PUNKTO_MNEMONIC env
                                             or prompt for phrase)
  punkto-key.py verify <atom.json>           verify an atom's signature

the atom file is a JSON object with at minimum 'punkto' and 't' fields.
verify expects 'sig' and 'pubkey' fields to also be present.
"""


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(USAGE)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "new":
        cmd_new()
    elif cmd == "import":
        cmd_import(args)
    elif cmd == "sign":
        if len(args) != 1:
            sys.exit("sign needs <atom.json>")
        cmd_sign(args[0])
    elif cmd == "verify":
        if len(args) != 1:
            sys.exit("verify needs <atom.json>")
        cmd_verify(args[0])
    else:
        sys.exit(USAGE)


if __name__ == "__main__":
    main()
