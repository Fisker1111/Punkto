/** Standalone Punkti 0.6 XY_Z candidate. No shipped v0.5.1 integration. */
const ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz';
const fail = message => { throw new RangeError(message); };

export function xyKey(xy, minimum = 1) {
  if (typeof xy !== 'string' || xy.length < minimum || xy.length > 12 ||
      [...xy].some(c => !ALPHABET.includes(c))) fail('geohash');
  return xy.padEnd(12, '0');
}

export function encodeXY(lat, lon, precision = 10) {
  if (!Number.isInteger(precision) || precision < 4 || precision > 12) fail('precision');
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) fail('coordinates');
  const bounds = [[-180, 180], [-90, 90]], coords = [lon, lat];
  let word = 0, result = '';
  for (let i = 0; i < precision * 5; i++) {
    const axis = i % 2, [low, high] = bounds[axis], mid = (low + high) / 2;
    const bit = coords[axis] >= mid ? 1 : 0;
    bounds[axis] = bit ? [mid, high] : [low, mid];
    word = word * 2 + bit;
    if (i % 5 === 4) { result += ALPHABET[word]; word = 0; }
  }
  return result;
}

export function decodeXY(xy) {
  xyKey(xy, 4);
  const bounds = [[-180, 180], [-90, 90]];
  let index = 0;
  for (const char of xy) {
    for (let shift = 4; shift >= 0; shift--) {
      const axis = index++ % 2, [low, high] = bounds[axis], mid = (low + high) / 2;
      bounds[axis] = ALPHABET.indexOf(char) & (1 << shift) ? [mid, high] : [low, mid];
    }
  }
  const [[lon_min, lon_max], [lat_min, lat_max]] = bounds;
  return {lat_min, lat_max, lon_min, lon_max, lat: (lat_min + lat_max) / 2, lon: (lon_min + lon_max) / 2};
}

export function parseZ(z) {
  // Full match via matched length also rejects a final newline (JS $ permits it).
  const match = typeof z === 'string' && /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/.exec(z);
  if (!match || match[0] !== z || z.length > 27 || z === '-0' ||
      (z.includes('.') && z.endsWith('0'))) fail('canonical Z');
  const [whole, fraction = ''] = z.split('.');
  return {coefficient: BigInt(whole + fraction), scale: fraction.length};
}

export function compareZ(a, b) {
  const left = parseZ(a), right = parseZ(b), scale = Math.max(left.scale, right.scale);
  const x = left.coefficient * 10n ** BigInt(scale - left.scale);
  const y = right.coefficient * 10n ** BigInt(scale - right.scale);
  return x < y ? -1 : x > y ? 1 : 0;
}

export function formatZ(value) {
  if (typeof value === 'string') { parseZ(value); return value; }
  let result;
  if (typeof value === 'bigint') result = value.toString();
  else {
    if (!Number.isFinite(value)) fail('finite height');
    // Exact binary rational -> nearest millimetre, ties to even. Avoid repr,
    // toFixed and floating multiplication changing a half-millimetre decision.
    const bytes = new DataView(new ArrayBuffer(8));
    bytes.setFloat64(0, Math.abs(value));
    const bits = bytes.getBigUint64(0), exponent = Number((bits >> 52n) & 2047n);
    const mantissa = (bits & ((1n << 52n) - 1n)) + (exponent ? 1n << 52n : 0n);
    const power = exponent ? exponent - 1023 - 52 : -1074;
    let numerator = mantissa * 1000n, denominator = 1n;
    if (power >= 0) numerator <<= BigInt(power);
    else denominator <<= BigInt(-power);
    let mm = numerator / denominator;
    const remainder = numerator % denominator;
    if (remainder * 2n > denominator || (remainder * 2n === denominator && mm % 2n)) mm++;
    const digits = mm.toString().padStart(4, '0');
    const fraction = digits.slice(-3).replace(/0+$/, '');
    result = (value < 0 && mm !== 0n ? '-' : '') + digits.slice(0, -3) + (fraction ? '.' + fraction : '');
  }
  parseZ(result);
  return result;
}

export function parseH(h) {
  if (typeof h !== 'string' || h.length > 32) fail('spatial address');
  if (h === '') return null;
  const parts = h.split('_');
  if (parts.length !== 2) fail('separator');
  xyKey(parts[0], 4); parseZ(parts[1]);
  return {xy: parts[0], z: parts[1]};
}

export function encodeH(lat, lon, height, precision = 10) {
  const h = encodeXY(lat, lon, precision) + '_' + formatZ(height);
  parseH(h);
  return h;
}

export function normalizeScope(scope = {}) {
  const keys = ['xy_lo', 'xy_hi', 'z_min', 'z_max'];
  if (scope === null || typeof scope !== 'object' || Array.isArray(scope) ||
      Object.keys(scope).some(k => !keys.includes(k))) fail('scope fields');
  const result = Object.fromEntries(keys.map(k => [k, Object.hasOwn(scope, k) ? scope[k] : null]));
  for (const [key, value] of Object.entries(result)) {
    if (value !== null) (key.startsWith('xy_') ? xyKey : parseZ)(value);
  }
  const {xy_lo: lo, xy_hi: hi, z_min: min, z_max: max} = result;
  if (lo !== null && hi !== null && xyKey(lo) >= xyKey(hi)) fail('equal or reversed XY');
  if (min !== null && max !== null && compareZ(min, max) >= 0) fail('equal or reversed Z');
  return result;
}

export function matches(h, scope = {}) {
  const s = normalizeScope(scope), parts = parseH(h);
  if (!parts) return Object.values(s).every(v => v === null);
  const {xy, z} = parts;
  return (s.xy_lo === null || xyKey(xy) >= xyKey(s.xy_lo)) &&
    (s.xy_hi === null || xyKey(xy) < xyKey(s.xy_hi)) &&
    (s.z_min === null || compareZ(z, s.z_min) >= 0) &&
    (s.z_max === null || compareZ(z, s.z_max) < 0);
}

export const subscribed = (h, scopes) => scopes.some(scope => matches(h, scope));
