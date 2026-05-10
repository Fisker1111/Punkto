#!/usr/bin/env python3
"""punkto-keygen v0.1 — mint a fresh Punkto identity.

A tiny, focused, single-file script. Run on any device with Python 3.8+ and
`cryptography`. Generates an Ed25519 keypair from a 12-word BIP39 mnemonic,
following punkto.identity.md v0.1.

  pip install cryptography
  python3 punkto-keygen-v0.1.py

This script ONLY generates new identities. For import / sign / verify, see
`punkto-key.py` in the same directory.

What it does:
  1. Reads 16 random bytes from the OS CSPRNG.
  2. Derives a 12-word BIP39 English mnemonic (4-bit SHA-256 checksum).
  3. Derives a 64-byte seed via PBKDF2-HMAC-SHA512 (2048 iters, salt='mnemonic').
  4. Takes the first 32 bytes as an Ed25519 private key seed.
  5. Derives the Ed25519 public key.
  6. Computes Author ID = base32_geohash(SHA-256(pubkey))[:12].
  7. Prints a printable identity card and an importable JSON blob.

The 12-word mnemonic is the ONLY secret. Write it down on paper. Store on
paper, in a password manager, or in encrypted cold storage. Never paste into
an AI agent or untrusted tool. The Pubkey + Author ID are safe to share.

Spec: see punkto.identity.md (https://github.com/Fisker1111/Punkto)
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sys
import urllib.request
from pathlib import Path
from typing import List

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    sys.stderr.write("This script needs `cryptography`:  pip install cryptography\n")
    sys.exit(1)

# Punkto canonical Base32 alphabet (same as Punkti / geohash3d)
GEOHASH_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"

# BIP39 English wordlist — fetched once and cached locally
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
    bits = (int.from_bytes(entropy, "big") << 4) | checksum
    return [words[(bits >> (11 * (11 - i))) & 0x7FF] for i in range(12)]


def mnemonic_to_seed(mnemonic: List[str]) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha512",
        " ".join(mnemonic).encode("utf-8"),
        b"mnemonic",
        2048,
        dklen=64,
    )


def base32_geohash(data: bytes) -> str:
    out = []
    bits = int.from_bytes(data, "big")
    nbits = len(data) * 8
    # pad to multiple of 5 on the right (low end)
    pad = (5 - nbits % 5) % 5
    bits <<= pad
    nbits += pad
    for i in range(nbits // 5 - 1, -1, -1):
        out.append(GEOHASH_ALPHABET[(bits >> (5 * i)) & 0x1F])
    return "".join(out)


def derive_identity(mnemonic: List[str]) -> dict:
    seed = mnemonic_to_seed(mnemonic)
    sk = Ed25519PrivateKey.from_private_bytes(seed[:32])
    pk_bytes = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pubkey_b64 = base64.b64encode(pk_bytes).decode("ascii")
    author_id = base32_geohash(hashlib.sha256(pk_bytes).digest())[:12]
    return {"author_id": author_id, "pubkey": pubkey_b64}


def print_card(mnemonic: List[str], identity: dict) -> None:
    aid = identity["author_id"]
    pk = identity["pubkey"]
    print()
    print("┌─────────────────────────────────────────────────────────────────┐")
    print("│  PUNKTO IDENTITY — KEEP SAFE, STORE OFFLINE                     │")
    print("├─────────────────────────────────────────────────────────────────┤")
    print(f"│  Author ID:  {aid}{' ' * (51 - len(aid))}│")
    print(f"│  Pubkey:     {pk}{' ' * (51 - len(pk))}│")
    print("│                                                                 │")
    print("│  Recovery phrase (12 words) — anyone with this IS you:          │")
    for i in range(4):
        a = f"{i+1:>2}. {mnemonic[i]:<10}"
        b = f"{i+5:>2}. {mnemonic[i+4]:<10}"
        c = f"{i+9:>2}. {mnemonic[i+8]:<10}"
        line = f"    {a}  {b}  {c}"
        print(f"│{line}{' ' * (65 - len(line))}│")
    print("└─────────────────────────────────────────────────────────────────┘")
    print()
    print("Next steps:")
    print("  1. WRITE DOWN the 12 words on paper. This is your only backup.")
    print("  2. Optionally save the JSON below to encrypted cold storage.")
    print("  3. The Pubkey + Author ID are safe to share.")
    print()
    print("JSON for import to PWA / cold storage:")
    blob = {
        "version": "punkto-identity-v0.1",
        "author_id": aid,
        "pubkey": pk,
        "mnemonic": mnemonic,
    }
    print(json.dumps(blob, indent=2))
    print()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    words = load_wordlist()
    entropy = secrets.token_bytes(16)
    mnemonic = entropy_to_mnemonic(entropy, words)
    identity = derive_identity(mnemonic)
    print_card(mnemonic, identity)
    return 0


if __name__ == "__main__":
    sys.exit(main())
