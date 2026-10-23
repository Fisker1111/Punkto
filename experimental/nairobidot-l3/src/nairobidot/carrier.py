"""Punkti reset: envelope, canonical bytes and provenance (no L4 semantics)."""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
import struct
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_C = 1024 * 1024
MAX_R = 2 * MAX_C
ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'
FIELDS = {'v', 't', 'h', 'x', 'alg', 'pk', 'refs', 'ext', 'sig'}


class StructuralError(ValueError):
    """Invalid carrier structure or canonical encoding."""


class ResourceError(ValueError):
    """Explicit resource refusal, separate from validation states."""


class State(str, Enum):
    VALID = 'VALID'
    ALGORITHM = 'UNVERIFIABLE-alg'
    STRUCTURAL = 'INVALID-structural'
    PROVENANCE = 'INVALID-provenance'
    KEY = 'UNVERIFIABLE-key'
    VERSION = 'OPAQUE-version'


def dumps(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def loads(raw: bytes | str, *, carrier: bool = False) -> Any:
    """Atom envelope: reject duplicate members and non-JSON constants."""
    def pairs(items: list) -> dict:
        out = {}
        for k, v in items:
            if k in out:
                raise StructuralError('duplicate-key')
            out[k] = v
        return out
    def constant(value: str) -> None:
        raise StructuralError('non-json-number')
    def integer(spelling: str) -> int:
        if carrier and not re.fullmatch(r'0|[1-9][0-9]*', spelling):
            raise StructuralError('timestamp spelling: expected 0|[1-9][0-9]*')
        return int(spelling)
    try:
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant,
                          parse_int=integer)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise StructuralError('json') from exc


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def unb64(value: str) -> bytes:
    try:
        if not isinstance(value, str):
            raise ValueError()
        data = base64.b64decode(value, validate=True)
        if b64(data) != value:
            raise ValueError()
        return data
    except (ValueError, binascii.Error) as exc:
        raise StructuralError('base64') from exc


def scalar(value: Any) -> bytes:
    if not isinstance(value, str):
        raise StructuralError('string-type')
    try:
        return value.encode('utf-8')
    except UnicodeError as exc:
        raise StructuralError('unicode-scalar') from exc


def address_ok(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r'([A-Za-z0-9./_-]{1,128}):([0-9a-f]+)', value)
    return bool(match and len(match[2]) % 2 == 0 and
                (match[1] not in ('punkti/0.6', 'punkti/0.5.1') or len(match[2]) == 64))


def lp(data: bytes) -> bytes:
    return struct.pack('>I', len(data)) + data


def canonical_body(atom: dict) -> bytes:
    """Reset §Canonical bytes: construct C after strict envelope checks."""
    if not isinstance(atom, dict) or set(atom) != FIELDS:
        raise StructuralError('envelope-fields')
    for field in FIELDS - {'t', 'refs'}:
        scalar(atom[field])
    if atom['v'] != 'punkti/0.6':
        raise StructuralError('version')
    if type(atom['t']) is not int or not 0 <= atom['t'] <= 9007199254740991:
        raise StructuralError('timestamp')
    h = atom['h']
    if h and (len(h) != 12 or any(c not in ALPHABET for c in h)):
        raise StructuralError('spatial-address')
    alg = atom['alg']
    if not alg or not alg.isascii() or len(alg) > 128:
        raise StructuralError('algorithm')
    pk, sig, ext = (unb64(atom[f]) for f in ('pk', 'sig', 'ext'))
    if not pk or not sig:
        raise StructuralError('empty-provenance')
    if alg == 'ed25519' and (len(pk) != 32 or len(sig) != 64):
        raise StructuralError('ed25519-length')
    refs = atom['refs']
    if not isinstance(refs, list):
        raise StructuralError('refs-type')
    if len(refs) > 256:
        raise ResourceError('refs-limit')
    chunks = [lp(scalar(atom['v'])), lp(str(atom['t']).encode('ascii')),
              lp(scalar(h)), lp(scalar(atom['x'])), lp(alg.encode('ascii')), lp(pk),
              struct.pack('>I', len(refs))]
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {'target', 'rel'}:
            raise StructuralError('reference-fields')
        target, rel = scalar(ref['target']), scalar(ref['rel'])
        if not address_ok(ref['target']):
            raise StructuralError('reference-target')
        if len(rel) > 1024:
            raise ResourceError('relation-limit')
        chunks.extend((lp(target), lp(rel)))
    chunks.append(lp(ext))
    body = b''.join(chunks)
    if len(body) > MAX_C:
        raise ResourceError('body-limit')
    return body


@dataclass(frozen=True)
class Record:
    """Exact transfer bytes and derived immutable addressing metadata."""
    atom: dict
    C: bytes
    R: bytes
    original_json: bytes | None = None

    @property
    def S(self) -> bytes:
        return b'PUNKTI-L3-SIGN\0' + self.C

    @property
    def mid(self) -> str:
        return hashlib.sha256(b'PUNKTI-L3-MID\0' + self.C).hexdigest()

    @property
    def address(self) -> str:
        return 'punkti/0.6:' + self.mid

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.R).hexdigest()

    def item(self) -> dict:
        return {'address': self.address, 'sha256': self.digest, 'record': b64(self.R)}


def from_atom(atom: dict, original: bytes | None = None) -> Record:
    body = canonical_body(atom)
    raw = lp(body) + lp(unb64(atom['sig']))
    if len(raw) > MAX_R:
        raise ResourceError('record-limit')
    return Record(loads(dumps(atom)), body, raw, original)


def import_json(raw: bytes | str) -> Record:
    return from_atom(loads(raw, carrier=True), raw.encode('utf-8') if isinstance(raw, str) else raw)


class Reader:
    def __init__(self, raw: bytes):
        self.raw, self.pos = raw, 0

    def take(self, n: int) -> bytes:
        if n > len(self.raw) - self.pos:
            raise StructuralError('truncated-frame')
        out = self.raw[self.pos:self.pos + n]
        self.pos += n
        return out

    def u32(self) -> int:
        return struct.unpack('>I', self.take(4))[0]

    def lp(self) -> bytes:
        return self.take(self.u32())

    def text(self) -> str:
        try:
            return self.lp().decode('utf-8')
        except UnicodeError as exc:
            raise StructuralError('utf8') from exc

    def finish(self) -> None:
        if self.pos != len(self.raw):
            raise StructuralError('trailing-frame')


def decode_record(raw: bytes) -> Record:
    """Reset §Canonical bytes: fully consume R and require canonical C equality."""
    if len(raw) > MAX_R:
        raise ResourceError('record-limit')
    outer = Reader(raw)
    body, sig = outer.lp(), outer.lp()
    outer.finish()
    if len(body) > MAX_C:
        raise ResourceError('body-limit')
    r = Reader(body)
    version, timestamp = r.text(), r.text()
    if not re.fullmatch(r'0|[1-9][0-9]{0,15}', timestamp):
        raise StructuralError('timestamp-spelling')
    atom = dict(v=version, t=int(timestamp), h=r.text(), x=r.text(), alg=r.text(), pk=b64(r.lp()))
    count = r.u32()
    if count > 256:
        raise ResourceError('refs-limit')
    atom['refs'] = [dict(target=r.text(), rel=r.text()) for _ in range(count)]
    atom['ext'], atom['sig'] = b64(r.lp()), b64(sig)
    r.finish()
    if canonical_body(atom) != body:
        raise StructuralError('noncanonical-body')
    return Record(atom, body, raw)


@dataclass(frozen=True)
class Validation:
    state: State
    reason: str
    record: Record | None = None


def validate(raw: bytes | str | dict | Record) -> Validation:
    """Reset §Validation state; resource failures deliberately propagate."""
    try:
        if isinstance(raw, Record):
            record = decode_record(raw.R)
        elif isinstance(raw, dict):
            record = from_atom(raw)
        elif isinstance(raw, str) or raw.lstrip().startswith(b'{'):
            record = import_json(raw)
        else:
            record = decode_record(raw)
    except StructuralError as exc:
        return Validation(State.STRUCTURAL, str(exc))
    if record.atom['alg'] != 'ed25519':
        return Validation(State.ALGORITHM, 'unsupported-algorithm', record)
    try:
        Ed25519PublicKey.from_public_bytes(unb64(record.atom['pk'])).verify(
            unb64(record.atom['sig']), record.S)
    except (InvalidSignature, ValueError):
        return Validation(State.PROVENANCE, 'signature-failed', record)
    return Validation(State.VALID, 'verified', record)
