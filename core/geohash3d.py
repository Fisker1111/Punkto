"""
geohash3d.py — 3D spatial geohash encoder/decoder for Punkto/Punkti protocol

Direct Python port of geohash3d.js.

Algorithm:
  - Base32 alphabet: '0123456789bcdefghjkmnpqrstuvwxyz'
  - 12 chars × 5 bits = 60 bits total
  - Split as 20 bits lat + 20 bits lon + 20 bits alt
  - Interleave order per bit position i (0-indexed from MSB):
      i%3 == 0 → lat bit
      i%3 == 1 → lon bit
      i%3 == 2 → alt bit
  - lat range : -90   to  90
  - lon range : -180  to  180
  - alt range : -500  to  8500  (9000 m total)
"""

from __future__ import annotations
from dataclasses import dataclass

BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz'
BASE32_MAP = {c: i for i, c in enumerate(BASE32)}

LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0
ALT_MIN, ALT_MAX = -500.0, 8500.0
BITS = 20          # bits per dimension
PRECISION = 12     # default char length


@dataclass
class Bounds3D:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    min_alt: float
    max_alt: float


@dataclass
class Decoded3D:
    lat: float
    lon: float
    alt: float
    error_lat: float
    error_lon: float
    error_alt: float


def _norm_to_int(val: float, min_: float, max_: float, bits: int) -> int:
    """Normalize a value in [min_, max_] to an integer in [0, 2^bits - 1]."""
    range_ = max_ - min_
    norm = (val - min_) / range_
    max_int = 1 << bits
    clamped = max(0.0, min(1.0 - 1e-15, norm))
    return int(clamped * max_int)


def encode(lat: float, lon: float, alt: float = 0.0, precision: int = PRECISION) -> str:
    """
    Encode lat, lon, alt into a Base32 3D geohash string.

    Args:
        lat:       latitude  in [-90, 90]
        lon:       longitude in [-180, 180]
        alt:       altitude  in [-500, 8500] metres (default 0)
        precision: number of output characters (default 12)

    Returns:
        Base32 geohash string of length `precision`
    """
    lat_int = _norm_to_int(lat, LAT_MIN, LAT_MAX, BITS)
    lon_int = _norm_to_int(lon, LON_MIN, LON_MAX, BITS)
    alt_int = _norm_to_int(alt, ALT_MIN, ALT_MAX, BITS)

    total_bits = precision * 5
    chars = []
    acc = 0
    acc_bits = 0

    for i in range(total_bits):
        dim = i % 3          # 0=lat, 1=lon, 2=alt
        dim_bit_idx = i // 3 # 0..19, MSB first within dimension
        bit_from_msb = BITS - 1 - dim_bit_idx

        if dim == 0:
            int_val = lat_int
        elif dim == 1:
            int_val = lon_int
        else:
            int_val = alt_int

        bit = (int_val >> bit_from_msb) & 1
        acc = (acc << 1) | bit
        acc_bits += 1

        if acc_bits == 5:
            chars.append(BASE32[acc])
            acc = 0
            acc_bits = 0

    return ''.join(chars)


def to_bounds(hash_str: str) -> Bounds3D:
    """
    Return the 3D bounding box of a geohash string.

    Args:
        hash_str: Base32 geohash string (1–12 chars)

    Returns:
        Bounds3D with min/max lat, lon, alt
    """
    length = len(hash_str)
    total_bits = length * 5

    lat_bits = lon_bits = alt_bits = 0
    for i in range(total_bits):
        dim = i % 3
        if dim == 0:
            lat_bits += 1
        elif dim == 1:
            lon_bits += 1
        else:
            alt_bits += 1

    lat_int = lon_int = alt_int = 0

    for i in range(total_bits):
        char_idx = i // 5
        bit_in_char = 4 - (i % 5)  # MSB first within char
        char_val = BASE32_MAP.get(hash_str[char_idx])
        if char_val is None:
            raise ValueError(f"Invalid Base32 character: {hash_str[char_idx]!r}")
        bit = (char_val >> bit_in_char) & 1
        dim = i % 3
        if dim == 0:
            lat_int = (lat_int << 1) | bit
        elif dim == 1:
            lon_int = (lon_int << 1) | bit
        else:
            alt_int = (alt_int << 1) | bit

    lat_max_int = 1 << lat_bits
    lon_max_int = 1 << lon_bits
    alt_max_int = 1 << alt_bits

    lat_range = LAT_MAX - LAT_MIN
    lon_range = LON_MAX - LON_MIN
    alt_range = ALT_MAX - ALT_MIN

    lat_cell = lat_range / lat_max_int
    lon_cell = lon_range / lon_max_int
    alt_cell = alt_range / alt_max_int

    min_lat = LAT_MIN + lat_int * lat_cell
    min_lon = LON_MIN + lon_int * lon_cell
    min_alt = ALT_MIN + alt_int * alt_cell

    return Bounds3D(
        min_lat=min_lat,
        max_lat=min_lat + lat_cell,
        min_lon=min_lon,
        max_lon=min_lon + lon_cell,
        min_alt=min_alt,
        max_alt=min_alt + alt_cell,
    )


def decode(hash_str: str) -> Decoded3D:
    """
    Decode a 3D geohash string into coordinates (center of cell) + errors.

    Args:
        hash_str: Base32 geohash string (1–12 chars)

    Returns:
        Decoded3D with lat, lon, alt and half-cell error per dimension
    """
    b = to_bounds(hash_str)
    return Decoded3D(
        lat=(b.min_lat + b.max_lat) / 2,
        lon=(b.min_lon + b.max_lon) / 2,
        alt=(b.min_alt + b.max_alt) / 2,
        error_lat=(b.max_lat - b.min_lat) / 2,
        error_lon=(b.max_lon - b.min_lon) / 2,
        error_alt=(b.max_alt - b.min_alt) / 2,
    )
