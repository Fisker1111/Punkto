const ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz';
const fail = message => { throw new RangeError(message); };

export function xy_key(xy, minimum = 1) {
  if (typeof xy !== 'string' || xy.length < minimum || xy.length > 12 || [...xy].some(c => !ALPHABET.includes(c))) {
    fail('geohash');
  }
  return xy.padEnd(12, '0');
}

export function encode_xy(lat, lon, precision = 10) {
  if (!Number.isInteger(precision) || precision < 4 || precision > 12) fail('precision');
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) fail('coordinates');
  const bounds = [[-180, 180], [-90, 90]];
  const coords = [lon, lat];
  let word = 0;
  let result = '';
  for (let index = 0; index < precision * 5; index++) {
    const axis = index % 2;
    const [low, high] = bounds[axis];
    const mid = (low + high) / 2;
    const bit = coords[axis] >= mid ? 1 : 0;
    bounds[axis] = bit ? [mid, high] : [low, mid];
    word = word * 2 + bit;
    if (index % 5 === 4) {
      result += ALPHABET[word];
      word = 0;
    }
  }
  return result;
}

export function decode_xy(xy) {
  xy_key(xy, 4);
  const bounds = [[-180, 180], [-90, 90]];
  let index = 0;
  for (const char of xy) {
    for (let shift = 4; shift >= 0; shift--) {
      const axis = index++ % 2;
      const [low, high] = bounds[axis];
      const mid = (low + high) / 2;
      bounds[axis] = ALPHABET.indexOf(char) & (1 << shift) ? [mid, high] : [low, mid];
    }
  }
  const [[lon_min, lon_max], [lat_min, lat_max]] = bounds;
  return {
    lat_min,
    lat_max,
    lon_min,
    lon_max,
    lat: (lat_min + lat_max) / 2,
    lon: (lon_min + lon_max) / 2,
  };
}

export function parse_z(z) {
  const match = typeof z === 'string' && /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/.exec(z);
  if (!match || match[0] !== z || z.length > 27 || z === '-0' || (z.includes('.') && z.endsWith('0'))) {
    fail('canonical Z');
  }
  const [whole, fraction = ''] = z.split('.');
  return { coefficient: BigInt(whole + fraction), scale: fraction.length };
}

export function compare_z(a, b) {
  const left = parse_z(a);
  const right = parse_z(b);
  const scale = Math.max(left.scale, right.scale);
  const x = left.coefficient * 10n ** BigInt(scale - left.scale);
  const y = right.coefficient * 10n ** BigInt(scale - right.scale);
  return x < y ? -1 : x > y ? 1 : 0;
}

export function format_z(value) {
  if (typeof value === 'string') {
    parse_z(value);
    return value;
  }
  let result;
  if (typeof value === 'bigint') {
    result = value.toString();
  } else {
    if (!Number.isFinite(value)) fail('finite height');
    const bytes = new DataView(new ArrayBuffer(8));
    bytes.setFloat64(0, Math.abs(value));
    const bits = bytes.getBigUint64(0);
    const exponent = Number((bits >> 52n) & 2047n);
    const mantissa = (bits & ((1n << 52n) - 1n)) + (exponent ? 1n << 52n : 0n);
    const power = exponent ? exponent - 1023 - 52 : -1074;
    let numerator = mantissa * 1000n;
    let denominator = 1n;
    if (power >= 0) numerator <<= BigInt(power);
    else denominator <<= BigInt(-power);
    let milli = numerator / denominator;
    const remainder = numerator % denominator;
    if (remainder * 2n > denominator || (remainder * 2n === denominator && milli % 2n)) milli++;
    const digits = milli.toString().padStart(4, '0');
    const fraction = digits.slice(-3).replace(/0+$/, '');
    result = (value < 0 && milli !== 0n ? '-' : '') + digits.slice(0, -3) + (fraction ? '.' + fraction : '');
  }
  parse_z(result);
  return result;
}

export function parse_h(h) {
  if (typeof h !== 'string' || h.length > 32) fail('spatial address');
  if (h === '') return null;
  const parts = h.split('_');
  if (parts.length !== 2) fail('separator');
  xy_key(parts[0], 4);
  parse_z(parts[1]);
  return { xy: parts[0], z: parts[1] };
}

export function encode_h(lat, lon, height, precision = 10) {
  const h = `${encode_xy(lat, lon, precision)}_${format_z(height)}`;
  parse_h(h);
  return h;
}

export function normalize_scope(scope = {}) {
  const keys = ['xy_lo', 'xy_hi', 'z_min', 'z_max'];
  if (scope === null || typeof scope !== 'object' || Array.isArray(scope) || Object.keys(scope).some(key => !keys.includes(key))) {
    fail('scope fields');
  }
  const normalized = Object.fromEntries(keys.map(key => [key, Object.hasOwn(scope, key) ? scope[key] : null]));
  for (const [key, value] of Object.entries(normalized)) {
    if (value !== null) {
      (key.startsWith('xy_') ? xy_key : parse_z)(value);
    }
  }
  if (normalized.xy_lo !== null && normalized.xy_hi !== null && xy_key(normalized.xy_lo) >= xy_key(normalized.xy_hi)) {
    fail('equal or reversed XY');
  }
  if (normalized.z_min !== null && normalized.z_max !== null && compare_z(normalized.z_min, normalized.z_max) >= 0) {
    fail('equal or reversed Z');
  }
  return normalized;
}

export function matches(h, scope = {}) {
  const normalized = normalize_scope(scope);
  const parsed = parse_h(h);
  if (!parsed) {
    return Object.values(normalized).every(value => value === null);
  }
  return (normalized.xy_lo === null || xy_key(parsed.xy) >= xy_key(normalized.xy_lo)) &&
    (normalized.xy_hi === null || xy_key(parsed.xy) < xy_key(normalized.xy_hi)) &&
    (normalized.z_min === null || compare_z(parsed.z, normalized.z_min) >= 0) &&
    (normalized.z_max === null || compare_z(parsed.z, normalized.z_max) < 0);
}

export function subscribed(h, scopes) {
  return scopes.some(scope => matches(h, scope));
}

export const xyKey = xy_key;
export const encodeXY = encode_xy;
export const decodeXY = decode_xy;
export const parseZ = parse_z;
export const formatZ = format_z;
export const compareZ = compare_z;
export const parseH = parse_h;
export const encodeH = encode_h;
export const normalizeScope = normalize_scope;
