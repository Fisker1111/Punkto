"""Canonical signing bytes and submit validation (no public-key registry)."""
import hashlib
import time

from core import geohash3d

FIELDS = ("t", "h", "x", "fp", "sig")
MIN_T = 1_577_836_800_000
DAY_MS = 86_400_000


class ValidationError(ValueError):
    pass


def signing_input(atom):
    return f"{int(atom['t'])}|{atom['h']}|{atom['x']}|{atom['fp']}".encode("utf-8")


def compute_mid(atom):
    return hashlib.sha256(signing_input(atom)).hexdigest()


def validate_atom(value, now_ms=None):
    """Return untouched canonical field values, computed MID and decoded point.

    Signature presence is checked as specified; signature verification requires
    an identity-to-public-key mapping outside this service's contract.
    """
    if not isinstance(value, dict) or any(k not in value for k in FIELDS):
        raise ValidationError("atom must contain t, h, x, fp, sig")
    atom = {k: value[k] for k in FIELDS}
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    if type(atom['t']) is not int or not MIN_T <= atom['t'] <= now_ms + DAY_MS:
        raise ValidationError("t must be integer milliseconds from 2020 through now + 1 day")
    h = atom['h']
    if not isinstance(h, str) or len(h) != 12:
        raise ValidationError("h must be a 12-character geohash")
    try:
        point = geohash3d.decode(h)
        if geohash3d.encode(point.lat, point.lon, point.alt) != h:
            raise ValueError("noncanonical geohash")
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    for key, bound in (("x", 4096), ("fp", 512)):
        if not isinstance(atom[key], str):
            raise ValidationError(f"{key} must be a string")
        try:
            size = len(atom[key].encode('utf-8'))
        except UnicodeError as exc:
            raise ValidationError(f"{key} must be valid UTF-8") from exc
        if size > bound:
            raise ValidationError(f"{key} exceeds {bound} UTF-8 bytes")
    if not isinstance(atom['sig'], str) or not atom['sig']:
        raise ValidationError("sig must be a non-empty string")
    try:
        atom['sig'].encode('utf-8')
    except UnicodeError as exc:
        raise ValidationError("sig must be valid UTF-8") from exc
    mid = compute_mid(atom)
    if 'mid' in value and value['mid'] != mid:
        raise ValidationError("mid does not match canonical signing input")
    return atom, mid, point
