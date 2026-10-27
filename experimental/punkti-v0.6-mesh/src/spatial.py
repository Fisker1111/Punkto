"""Punkti 0.6 XY_Z: 2D geohash, exact decimal height, lower-edge scopes."""
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import math
import re

ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'


def xy_key(xy, minimum=1):
    if not isinstance(xy, str) or not minimum <= len(xy) <= 12 or any(c not in ALPHABET for c in xy):
        raise ValueError('geohash')
    return xy.ljust(12, '0')


def encode_xy(lat, lon, precision=10):
    if type(precision) is not int or not 4 <= precision <= 12:
        raise ValueError('precision')
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('coordinates')
    bounds = [[-180., 180.], [-90., 90.]]
    coords = (lon, lat)
    out, word = '', 0
    for i in range(precision * 5):
        low, high = bounds[i % 2]
        mid = (low + high) / 2
        bit = int(coords[i % 2] >= mid)
        bounds[i % 2] = [mid, high] if bit else [low, mid]
        word = (word << 1) | bit
        if i % 5 == 4:
            out += ALPHABET[word]
            word = 0
    return out


def decode_xy(xy):
    xy_key(xy, 4)
    bounds = [[-180., 180.], [-90., 90.]]
    for i, bit in enumerate(''.join(f'{ALPHABET.index(c):05b}' for c in xy)):
        low, high = bounds[i % 2]
        mid = (low + high) / 2
        bounds[i % 2] = [mid, high] if bit == '1' else [low, mid]
    (lon_min, lon_max), (lat_min, lat_max) = bounds
    return dict(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max,
                lat=(lat_min + lat_max) / 2, lon=(lon_min + lon_max) / 2)


def parse_z(z):
    if (not isinstance(z, str) or not 1 <= len(z) <= 27 or
            not re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?', z) or
            z == '-0' or ('.' in z and z.endswith('0'))):
        raise ValueError('canonical Z')
    return Decimal(z)


def format_z(value):
    if isinstance(value, str):
        parse_z(value)
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('finite height')
        with localcontext() as ctx:
            ctx.prec = 400
            value = Decimal.from_float(value).quantize(Decimal('.001'), rounding=ROUND_HALF_EVEN)
    elif type(value) is int:
        value = Decimal(value)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError('height')
    z = format(value, 'f')
    if '.' in z:
        z = z.rstrip('0').rstrip('.')
    if value == 0:
        z = '0'
    parse_z(z)
    return z


def compare_z(a, b):
    a, b = parse_z(a), parse_z(b)
    return (a > b) - (a < b)


def parse_h(h):
    if not isinstance(h, str) or len(h) > 32:
        raise ValueError('spatial address')
    if h == '':
        return None
    if h.count('_') != 1:
        raise ValueError('separator')
    xy, z = h.split('_')
    xy_key(xy, 4)
    parse_z(z)
    return xy, z


def encode_h(lat, lon, height, precision=10):
    h = encode_xy(lat, lon, precision) + '_' + format_z(height)
    parse_h(h)
    return h


def altitude(h):
    parts = parse_h(h)
    if parts is None:
        raise ValueError('unanchored')
    return parse_z(parts[1])


@dataclass(frozen=True)
class Subscription:
    xy_lo: str | None = None
    xy_hi: str | None = None
    z_min: str | None = None
    z_max: str | None = None

    def __post_init__(self):
        for bound in (self.xy_lo, self.xy_hi):
            if bound is not None:
                xy_key(bound)
        for bound in (self.z_min, self.z_max):
            if bound is not None:
                parse_z(bound)
        if self.xy_lo is not None and self.xy_hi is not None and xy_key(self.xy_lo) >= xy_key(self.xy_hi):
            raise ValueError('equal or reversed bounds: xy')
        if self.z_min is not None and self.z_max is not None and compare_z(self.z_min, self.z_max) >= 0:
            raise ValueError('equal or reversed bounds: z')

    def matches(self, h):
        parts = parse_h(h)
        if parts is None:
            return all(v is None for v in asdict(self).values())
        xy, z = parts
        return ((self.xy_lo is None or xy_key(xy) >= xy_key(self.xy_lo)) and
                (self.xy_hi is None or xy_key(xy) < xy_key(self.xy_hi)) and
                (self.z_min is None or compare_z(z, self.z_min) >= 0) and
                (self.z_max is None or compare_z(z, self.z_max) < 0))

    def wire(self):
        return asdict(self)
