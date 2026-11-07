"""Standard GeoHash, longitude first. decode returns cell bounds and center."""
import math

ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'


def _check(lat, lon, precision):
    if type(precision) is not int or not 1 <= precision <= 12:
        raise ValueError('precision')
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('coordinates')


def encode(lat, lon, precision=10):
    _check(lat, lon, precision)
    bounds = [[-180., 180.], [-90., 90.]]
    result, word = '', 0
    for i in range(5 * precision):
        axis = i % 2
        low, high = bounds[axis]
        mid = (low + high) / 2
        bit = int((lon, lat)[axis] >= mid)
        bounds[axis] = [mid, high] if bit else [low, mid]
        word = word * 2 + bit
        if i % 5 == 4:
            result += ALPHABET[word]
            word = 0
    return result


def encode_independent(lat, lon, precision=10):
    """Quantize axes to integer grids, then interleave their binary strings."""
    _check(lat, lon, precision)
    nlon = (precision * 5 + 1) // 2
    nlat = precision * 5 // 2
    x = min(2**nlon - 1, int((lon + 180) / 360 * 2**nlon))
    y = min(2**nlat - 1, int((lat + 90) / 180 * 2**nlat))
    xb, yb = format(x, f'0{nlon}b'), format(y, f'0{nlat}b')
    bits = ''.join(a + b for a, b in zip(xb, yb))
    if nlon > nlat:
        bits += xb[-1]
    return ''.join(ALPHABET[int(bits[i:i + 5], 2)] for i in range(0, len(bits), 5))


def decode(prefix):
    if not isinstance(prefix, str) or not 1 <= len(prefix) <= 12 or any(c not in ALPHABET for c in prefix):
        raise ValueError('prefix')
    bounds = [[-180., 180.], [-90., 90.]]
    bits = ''.join(format(ALPHABET.index(c), '05b') for c in prefix)
    for i, bit in enumerate(bits):
        low, high = bounds[i % 2]
        mid = (low + high) / 2
        bounds[i % 2] = [mid, high] if bit == '1' else [low, mid]
    (west, east), (south, north) = bounds
    return dict(lat=(south + north) / 2, lon=(west + east) / 2,
                lat_min=south, lat_max=north, lon_min=west, lon_max=east)
