"""XY_Z profile candidate: independent scalar codec and range interpretation."""
from __future__ import annotations
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import math
import re

BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz'
KEYS = {'xy_lo', 'xy_hi', 'z_min', 'z_max'}


def fail(reason):
    # Delayed dependency keeps the carrier able to use the address parser.
    from .carrier import StructuralError
    raise StructuralError(reason)


def xy_key(value, minimum=1):
    if type(value) is not str or not minimum <= len(value) <= 12:
        fail('xy-length')
    if set(value) - set(BASE32):
        fail('xy-alphabet')
    return value + '0' * (12 - len(value))


def encode_xy(lat, lon, precision=10):
    if type(precision) is not int or precision not in range(4, 13):
        fail('xy-precision')
    for coordinate, extent in ((lat, 90), (lon, 180)):
        if not math.isfinite(coordinate) or abs(coordinate) > extent:
            fail('xy-coordinate')
    west, east, south, north = -180., 180., -90., 90.
    bits = []
    for index in range(5 * precision):
        if index & 1:
            middle = (south + north) / 2
            upper = lat >= middle
            if upper: south = middle
            else: north = middle
        else:
            middle = (west + east) / 2
            upper = lon >= middle
            if upper: west = middle
            else: east = middle
        bits.append('1' if upper else '0')
    return ''.join(BASE32[int(''.join(bits[n:n+5]), 2)] for n in range(0, len(bits), 5))


def decode_xy(value):
    xy_key(value, 4)
    west, east, south, north = -180., 180., -90., 90.
    longitude = True
    for char in value:
        word = BASE32.index(char)
        for shift in (4, 3, 2, 1, 0):
            upper = word & (1 << shift)
            if longitude:
                mid = (west + east) / 2
                if upper: west = mid
                else: east = mid
            else:
                mid = (south + north) / 2
                if upper: south = mid
                else: north = mid
            longitude = not longitude
    return {'lat_min': south, 'lat_max': north, 'lon_min': west, 'lon_max': east,
            'lat': (south + north) / 2, 'lon': (west + east) / 2}


def parse_z(value):
    if type(value) is not str or len(value) not in range(1, 28):
        fail('z-type-length')
    if re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?', value) is None or value == '-0':
        fail('z-spelling')
    return Decimal(value)


def compare_z(left, right):
    left, right = parse_z(left), parse_z(right)
    if left == right: return 0
    return -1 if left < right else 1


def format_z(height):
    if type(height) is str:
        parse_z(height)
        return height
    if type(height) not in (int, float, Decimal):
        fail('height-type')
    exact = Decimal.from_float(height) if type(height) is float else Decimal(height)
    if not exact.is_finite():
        fail('height-finite')
    if type(height) is float:
        with localcontext() as context:
            context.prec = 400
            exact = exact.quantize(Decimal('0.001'), rounding=ROUND_HALF_EVEN)
    if exact.is_zero():
        return '0'
    whole, dot, fraction = format(exact, 'f').partition('.')
    fraction = fraction.rstrip('0')
    spelling = whole + ('.' + fraction if fraction else '')
    parse_z(spelling)
    return spelling


def parse_h(address):
    if type(address) is not str or len(address) > 32:
        fail('address-type-length')
    if address == '': return None
    fields = address.split('_')
    if len(fields) != 2:
        fail('address-separator')
    xy_key(fields[0], 4)
    parse_z(fields[1])
    return tuple(fields)


def encode_h(lat, lon, height, precision=10):
    result = '{}_{}'.format(encode_xy(lat, lon, precision), format_z(height))
    parse_h(result)
    return result


def altitude(address):
    pair = parse_h(address)
    if pair is None: fail('unanchored-height')
    return parse_z(pair[1])


def normalize(scope):
    if type(scope) is not dict or set(scope) - KEYS:
        fail('scope-fields')
    normalized = dict.fromkeys(sorted(KEYS))
    normalized.update(scope)
    for key, value in normalized.items():
        if value is not None:
            (xy_key if key.startswith('xy_') else parse_z)(value)
    low, high = normalized['xy_lo'], normalized['xy_hi']
    if low is not None and high is not None and xy_key(low) >= xy_key(high):
        fail('equal or reversed bounds')
    low, high = normalized['z_min'], normalized['z_max']
    if low is not None and high is not None and compare_z(low, high) >= 0:
        fail('equal or reversed bounds')
    return normalized


def matches(h, scope):
    selection = normalize(scope)
    if h is None:
        return all(v is None for v in selection.values())
    pair = parse_h(h)
    if pair is None:
        return all(v is None for v in selection.values())
    xy, z = pair
    for member, bound in selection.items():
        if bound is None: continue
        if member.startswith('xy_'):
            result = (xy_key(xy) > xy_key(bound)) - (xy_key(xy) < xy_key(bound))
        else:
            result = compare_z(z, bound)
        if member in ('xy_lo', 'z_min') and result < 0: return False
        if member in ('xy_hi', 'z_max') and result >= 0: return False
    return True


def subscribed(h, scopes):
    return any(matches(h, scope) for scope in scopes)
