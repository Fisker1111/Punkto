"""Mesh §Subscriptions: provisional interleaved XYZ and literal ranges."""
from __future__ import annotations
import math
from .carrier import ALPHABET, StructuralError

KEYS = {'h_lo', 'h_hi', 'z_min', 'z_max'}


def normalize(scope: dict) -> dict:
    if not isinstance(scope, dict) or set(scope) - KEYS:
        raise StructuralError('scope-fields')
    result = {key: scope.get(key) for key in sorted(KEYS)}
    for key in ('h_lo', 'h_hi'):
        value = result[key]
        if value is not None and (not isinstance(value, str) or not 1 <= len(value) <= 12
                                  or any(c not in ALPHABET for c in value)):
            raise StructuralError('scope-h')
    for key in ('z_min', 'z_max'):
        value = result[key]
        if value is not None:
            if type(value) not in (int, float):
                raise StructuralError('scope-z')
            try:
                if not math.isfinite(value):
                    raise StructuralError('scope-z')
            except OverflowError as exc:
                raise StructuralError('scope-z') from exc
    return result


def altitude(h: str) -> float:
    """Third bit of each latitude/longitude/altitude triplet, MSB first."""
    if len(h) != 12 or any(c not in ALPHABET for c in h):
        raise StructuralError('spatial-address')
    bits = ''.join(f'{ALPHABET.index(c):05b}' for c in h)
    z = int(bits[2::3], 2)
    return -500 + (z + 0.5) * 9000 / 2**20


def matches(h: str | None, scope: dict) -> bool:
    s = normalize(scope)
    if all(v is None for v in s.values()):
        return True
    if not h:
        return False
    if s['h_lo'] is not None and h < s['h_lo']:
        return False
    if s['h_hi'] is not None and h >= s['h_hi']:
        return False
    if s['z_min'] is not None or s['z_max'] is not None:
        z = altitude(h)
        if s['z_min'] is not None and z < s['z_min']:
            return False
        if s['z_max'] is not None and z >= s['z_max']:
            return False
    return True


def subscribed(h: str | None, scopes: list[dict]) -> bool:
    return any(matches(h, scope) for scope in scopes)
