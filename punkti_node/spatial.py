"""Provisional 60-bit 3D profile; standalone, no production imports."""
from dataclasses import asdict, dataclass
import math
from carrier import ALPHABET


def altitude(h):
    if len(h) != 12 or any(c not in ALPHABET for c in h):
        raise ValueError('12-character spatial address required')
    bits = ''.join(f'{ALPHABET.index(c):05b}' for c in h)
    z = int(bits[2::3], 2)
    return -500 + (z + 0.5) * 9000 / (1 << 20)


@dataclass(frozen=True)
class Subscription:
    h_lo: str | None = None
    h_hi: str | None = None
    z_min: float | None = None
    z_max: float | None = None

    def __post_init__(self):
        for bound in (self.h_lo, self.h_hi):
            if bound is not None and (not isinstance(bound, str) or not 1 <= len(bound) <= 12
                                      or any(c not in ALPHABET for c in bound)):
                raise ValueError('geohash bound')
        if self.h_lo is not None and self.h_hi is not None and self.h_lo >= self.h_hi:
            raise ValueError('empty/reversed h interval')
        for bound in (self.z_min, self.z_max):
            if bound is not None and (type(bound) not in (int, float) or not math.isfinite(bound)):
                raise ValueError('finite elevation required')
        if self.z_min is not None and self.z_max is not None and self.z_min >= self.z_max:
            raise ValueError('empty/reversed z interval')

    def matches(self, h):
        scoped = any(v is not None for v in asdict(self).values())
        if not h:
            return not scoped
        if self.h_lo is not None and h < self.h_lo:
            return False
        if self.h_hi is not None and h >= self.h_hi:
            return False
        if self.z_min is not None or self.z_max is not None:
            z = altitude(h)
            return ((self.z_min is None or z >= self.z_min) and
                    (self.z_max is None or z < self.z_max))
        return True

    def wire(self):
        return asdict(self)
