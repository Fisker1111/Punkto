"""
punkto.py — Punkto core library v0.1

Canonical address operations: make, parse, validate, decode,
and conversion between canonical, URI, and HTTPS forms.

Canonical form  :  p:<spatial>-<id>     (identity, signing, storage)
URI form        :  punkto://<spatial>/<id>     (navigation)
HTTPS form      :  https://punkto.xyz/p/<spatial>/<id>    (web sharing)

All derived forms resolve to exactly one canonical Punkto.
Canonical first. Everything else is translation.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Optional

from . import geohash3d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HTTPS_HOST = 'https://punkto.xyz'

# Canonical regex:  p:<12 base32 chars>  optionally followed by  -<id>
_CANONICAL_RE = re.compile(r'^p:([0-9a-z]{12})(?:-([A-Za-z0-9]+))?$')
_SPATIAL_RE   = re.compile(r'^[0-9a-z]{12}$')
_ID_RE        = re.compile(r'^[A-Za-z0-9]+$')

# URI scheme prefix
_URI_PREFIX   = 'punkto://'
_HTTPS_PREFIX = f'{HTTPS_HOST}/p/'


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Punkto:
    """Parsed Punkto address."""
    spatial: str            # 12-char base32 3D geohash
    id: Optional[str]       # optional short identifier (alphanumeric)

    def __str__(self) -> str:
        """Return canonical form."""
        return canonical(self)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Punkto):
            return self.spatial == other.spatial and self.id == other.id
        if isinstance(other, str):
            try:
                return self == parse(other)
            except ValueError:
                return False
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.spatial, self.id))


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def make(
    lat: float,
    lon: float,
    alt: float = 0.0,
    id: Optional[str] = None,
) -> str:
    """
    Generate a canonical Punkto address from coordinates.

    Args:
        lat:  latitude  in [-90, 90]
        lon:  longitude in [-180, 180]
        alt:  altitude  in [-500, 8500] metres (default 0)
        id:   optional alphanumeric identifier; auto-generated if not provided

    Returns:
        Canonical Punkto string, e.g. ``p:u07qsuustfsh-a3b9c1``
    """
    spatial = geohash3d.encode(lat, lon, alt)
    if id is None:
        id = short_id()
    if not _ID_RE.match(id):
        raise ValueError(f"id must be alphanumeric, got {id!r}")
    return f'p:{spatial}-{id}'


def make_bare(lat: float, lon: float, alt: float = 0.0) -> str:
    """
    Generate a canonical Punkto address without an id component.

    Use this when the Punkto identifies a spatial region only, not a record.

    Returns:
        Canonical Punkto string, e.g. ``p:u07qsuustfsh``
    """
    spatial = geohash3d.encode(lat, lon, alt)
    return f'p:{spatial}'


def validate(s: str) -> bool:
    """Return True if ``s`` is a valid canonical Punkto string."""
    return bool(_CANONICAL_RE.match(s))


def parse(s: str) -> Punkto:
    """
    Parse a canonical Punkto string into a Punkto dataclass.

    Args:
        s: canonical Punkto string

    Returns:
        Punkto(spatial, id)

    Raises:
        ValueError: if the string is not a valid canonical Punkto
    """
    m = _CANONICAL_RE.match(s)
    if not m:
        raise ValueError(
            f"Invalid canonical Punkto: {s!r}. "
            f"Expected p:<12-char-geohash> or p:<12-char-geohash>-<id>"
        )
    return Punkto(spatial=m.group(1), id=m.group(2))


def canonical(p: Punkto) -> str:
    """Return the canonical string for a Punkto dataclass."""
    if p.id:
        return f'p:{p.spatial}-{p.id}'
    return f'p:{p.spatial}'


def decode(s: str) -> geohash3d.Decoded3D:
    """
    Decode a canonical Punkto string into 3D coordinates.

    Returns the center of the geohash cell with error bounds.

    Args:
        s: canonical Punkto string

    Returns:
        Decoded3D(lat, lon, alt, error_lat, error_lon, error_alt)
    """
    p = parse(s)
    return geohash3d.decode(p.spatial)


def spatial_prefix(s: str, length: int = 4) -> str:
    """
    Return the spatial prefix of a Punkto (useful for proximity queries).

    Args:
        s:      canonical Punkto string
        length: number of geohash prefix chars (default 4 ≈ regional)

    Returns:
        prefix string of length ``length``
    """
    p = parse(s)
    if length < 1 or length > 12:
        raise ValueError(f"length must be 1–12, got {length}")
    return p.spatial[:length]


def near(a: str, b: str, prefix_length: int = 8) -> bool:
    """
    Return True if two Punktos share the same geohash prefix.

    Args:
        a, b:          canonical Punkto strings
        prefix_length: chars to compare (default 8 ≈ ~1 m radius)
    """
    pa = parse(a)
    pb = parse(b)
    return pa.spatial[:prefix_length] == pb.spatial[:prefix_length]


# ---------------------------------------------------------------------------
# Format conversions
# ---------------------------------------------------------------------------

def to_uri(s: str) -> str:
    """
    Convert canonical Punkto to URI form.

    ``p:u07qsuustfsh-9xk3``  →  ``punkto://u07qsuustfsh/9xk3``
    """
    p = parse(s)
    if p.id:
        return f'{_URI_PREFIX}{p.spatial}/{p.id}'
    return f'{_URI_PREFIX}{p.spatial}'


def from_uri(uri: str) -> str:
    """
    Convert URI form back to canonical Punkto.

    ``punkto://u07qsuustfsh/9xk3``  →  ``p:u07qsuustfsh-9xk3``

    Raises:
        ValueError: if the URI is not a valid Punkto URI
    """
    if not uri.startswith(_URI_PREFIX):
        raise ValueError(f"Not a Punkto URI: {uri!r}")
    rest = uri[len(_URI_PREFIX):]
    parts = rest.split('/', 1)
    spatial = parts[0]
    id_ = parts[1] if len(parts) > 1 else None
    if not _SPATIAL_RE.match(spatial):
        raise ValueError(f"Invalid spatial component in URI: {spatial!r}")
    if id_ and not _ID_RE.match(id_):
        raise ValueError(f"Invalid id component in URI: {id_!r}")
    p = Punkto(spatial=spatial, id=id_)
    return canonical(p)


def to_https(s: str) -> str:
    """
    Convert canonical Punkto to HTTPS web URL.

    ``p:u07qsuustfsh-9xk3``  →  ``https://punkto.xyz/p/u07qsuustfsh/9xk3``
    """
    p = parse(s)
    if p.id:
        return f'{_HTTPS_PREFIX}{p.spatial}/{p.id}'
    return f'{_HTTPS_PREFIX}{p.spatial}'


def from_https(url: str) -> str:
    """
    Convert HTTPS web URL back to canonical Punkto.

    ``https://punkto.xyz/p/u07qsuustfsh/9xk3``  →  ``p:u07qsuustfsh-9xk3``

    Raises:
        ValueError: if the URL is not a valid Punkto HTTPS URL
    """
    if not url.startswith(_HTTPS_PREFIX):
        raise ValueError(f"Not a Punkto HTTPS URL: {url!r}")
    rest = url[len(_HTTPS_PREFIX):]
    parts = rest.split('/', 1)
    spatial = parts[0]
    id_ = parts[1] if len(parts) > 1 else None
    if not _SPATIAL_RE.match(spatial):
        raise ValueError(f"Invalid spatial component in URL: {spatial!r}")
    if id_ and not _ID_RE.match(id_):
        raise ValueError(f"Invalid id component in URL: {id_!r}")
    p = Punkto(spatial=spatial, id=id_)
    return canonical(p)


def resolve(s: str) -> str:
    """
    Resolve any valid Punkto representation to canonical form.

    Accepts: canonical, punkto:// URI, https://punkto.xyz/p/ URL.

    Raises:
        ValueError: if the input cannot be resolved to a canonical Punkto
    """
    if s.startswith('p:'):
        p = parse(s)         # validates; raises on bad input
        return canonical(p)
    if s.startswith(_URI_PREFIX):
        return from_uri(s)
    if s.startswith(_HTTPS_PREFIX):
        return from_https(s)
    raise ValueError(
        f"Cannot resolve to canonical Punkto: {s!r}. "
        f"Expected p:, punkto://, or {_HTTPS_PREFIX} prefix."
    )


def equals(a: str, b: str) -> bool:
    """
    Return True if two Punkto representations refer to the same canonical address.

    Works across canonical, URI, and HTTPS forms.
    """
    try:
        return resolve(a) == resolve(b)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def short_id(length: int = 6) -> str:
    """
    Generate a random alphanumeric identifier.

    Args:
        length: number of characters (default 6)

    Returns:
        Lowercase alphanumeric string, e.g. ``'a3b9c1'``
    """
    alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def human_label(s: str, place: Optional[str] = None) -> str:
    """
    Return a human-readable label for a Punkto.

    Args:
        s:     canonical Punkto string
        place: optional place name (e.g. 'Copenhagen')

    Returns:
        e.g. ``'Copenhagen / 42m'`` or ``'u07qsuustfsh / 42m'``
    """
    coords = decode(s)
    alt_m = round(coords.alt)
    name = place if place else parse(s).spatial[:8]
    return f'{name} / {alt_m}m'
