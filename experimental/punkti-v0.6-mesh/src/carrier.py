"""Candidate Punkti 0.6 carrier. No application or identity semantics."""
import base64
import hashlib
import json
import re
import struct
from dataclasses import dataclass
from enum import Enum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

VERSION = 'punkti/0.6'
ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'
BODY_LIMIT = 1024 * 1024
RECORD_LIMIT = 2 * BODY_LIMIT
SIGN_DOMAIN = b'PUNKTI-L3-SIGN\0'
MID_DOMAIN = b'PUNKTI-L3-MID\0'
FIELDS = {'v', 't', 'h', 'x', 'alg', 'pk', 'refs', 'ext', 'sig'}


class State(str, Enum):
    VALID = 'VALID'
    ALGORITHM = 'UNVERIFIABLE-alg'
    STRUCTURAL = 'INVALID-structural'
    PROVENANCE = 'INVALID-provenance'
    KEY = 'UNVERIFIABLE-key'  # Reserved for a separate legacy adapter.
    VERSION = 'OPAQUE-version'


class ResourceLimit(ValueError):
    """Local resource refusal, not a validity judgment."""


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def unb64(text):
    if not isinstance(text, str):
        raise ValueError('base64 string required')
    raw = base64.b64decode(text, validate=True)
    if b64(raw) != text:
        raise ValueError('noncanonical base64')
    return raw


def lp(raw):
    return struct.pack('>I', len(raw)) + raw


def utf8(text):
    if not isinstance(text, str):
        raise ValueError('string required')
    return text.encode('utf-8', errors='strict')


def address_ok(address):
    if not isinstance(address, str):
        return False
    match = re.fullmatch(r'([A-Za-z0-9./_-]{1,128}):([0-9a-f]+)', address)
    return bool(match and len(match[2]) % 2 == 0 and
                (match[1] not in ('punkti/0.5.1', VERSION) or len(match[2]) == 64))


def canonical(atom):
    if not isinstance(atom, dict) or set(atom) != FIELDS or atom['v'] != VERSION:
        raise ValueError('envelope fields/version')
    if type(atom['t']) is not int or not 0 <= atom['t'] <= 9007199254740991:
        raise ValueError('timestamp')
    h = atom['h']
    if not isinstance(h, str) or (h and (len(h) != 12 or any(c not in ALPHABET for c in h))):
        raise ValueError('spatial address')
    alg = utf8(atom['alg'])
    if not 1 <= len(alg) <= 128 or not alg.isascii():
        raise ValueError('algorithm')
    pk, sig, ext = (unb64(atom[k]) for k in ('pk', 'sig', 'ext'))
    if not pk or not sig:
        raise ValueError('empty key/signature')
    if atom['alg'] == 'ed25519' and (len(pk) != 32 or len(sig) != 64):
        raise ValueError('ed25519 encoding lengths')
    refs = atom['refs']
    if not isinstance(refs, list):
        raise ValueError('references array')
    if len(refs) > 256:
        raise ResourceLimit('reference limit')
    chunks = [lp(utf8(atom['v'])), lp(str(atom['t']).encode('ascii')),
              lp(utf8(h)), lp(utf8(atom['x'])), lp(alg), lp(pk), struct.pack('>I', len(refs))]
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {'target', 'rel'} or not address_ok(ref['target']):
            raise ValueError('reference')
        rel = utf8(ref['rel'])
        if len(rel) > 1024:
            raise ResourceLimit('relation limit')
        chunks.extend((lp(utf8(ref['target'])), lp(rel)))
    chunks.append(lp(ext))
    body = b''.join(chunks)
    if len(body) > BODY_LIMIT:
        raise ResourceLimit('body limit')
    return body


class Reader:
    def __init__(self, raw):
        self.raw, self.pos = raw, 0

    def take(self, size):
        if size > len(self.raw) - self.pos:
            raise ValueError('truncated framing')
        result = self.raw[self.pos:self.pos + size]
        self.pos += size
        return result

    def count(self):
        return struct.unpack('>I', self.take(4))[0]

    def field(self):
        return self.take(self.count())

    def text(self):
        return self.field().decode('utf-8', errors='strict')

    def end(self):
        if self.pos != len(self.raw):
            raise ValueError('trailing bytes')


def record(atom):
    result = lp(canonical(atom)) + lp(unb64(atom['sig']))
    if len(result) > RECORD_LIMIT:
        raise ResourceLimit('record limit')
    return result


def decode(raw):
    if len(raw) > RECORD_LIMIT:
        raise ResourceLimit('record limit')
    outer = Reader(raw)
    body, sig = outer.field(), outer.field()
    outer.end()
    if len(body) > BODY_LIMIT:
        raise ResourceLimit('body limit')
    r = Reader(body)
    version = r.text()
    if version != VERSION:
        raise ValueError('unsupported version requires opaque wrapper')
    decimal = r.text()
    if not re.fullmatch(r'0|[1-9][0-9]{0,15}', decimal):
        raise ValueError('noncanonical timestamp')
    atom = dict(v=version, t=int(decimal), h=r.text(), x=r.text(), alg=r.text(), pk=b64(r.field()))
    count = r.count()
    if count > 256:
        raise ResourceLimit('reference limit')
    atom['refs'] = [dict(target=r.text(), rel=r.text()) for _ in range(count)]
    atom['ext'], atom['sig'] = b64(r.field()), b64(sig)
    r.end()
    if canonical(atom) != body:
        raise ValueError('noncanonical body')
    return atom, body, sig


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON key')
        obj[key] = value
    return obj


def reject_number(_):
    raise ValueError('noninteger JSON number')


def unsigned_integer(spelling):
    if not re.fullmatch(r'0|[1-9][0-9]*', spelling):
        raise ValueError('timestamp spelling: expected 0|[1-9][0-9]*')
    return int(spelling)


def import_json(raw):
    """Import only; no byte-exact JSON export is offered. R is the wire format."""
    if len(raw) > RECORD_LIMIT:
        raise ResourceLimit('JSON transport limit')
    atom = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                      parse_int=unsigned_integer, parse_float=reject_number, parse_constant=reject_number)
    return record(atom)


@dataclass(frozen=True)
class Observation:
    state: State
    address: str | None = None
    h: str | None = None


def validate(raw):
    try:
        atom, body, sig = decode(raw)
    except ResourceLimit:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, struct.error):
        return Observation(State.STRUCTURAL)
    address = VERSION + ':' + hashlib.sha256(MID_DOMAIN + body).hexdigest()
    if atom['alg'] != 'ed25519':
        return Observation(State.ALGORITHM, address, atom['h'])
    try:
        Ed25519PublicKey.from_public_bytes(unb64(atom['pk'])).verify(sig, SIGN_DOMAIN + body)
    except (InvalidSignature, ValueError):
        return Observation(State.PROVENANCE, address, atom['h'])
    return Observation(State.VALID, address, atom['h'])
