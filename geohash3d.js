/**
 * geohash3d.js — 3D spatial geohash encoder/decoder for Punkto/Punkti protocol
 *
 * Algorithm:
 *   - Base32 alphabet: '0123456789bcdefghjkmnpqrstuvwxyz'
 *   - 12 chars × 5 bits = 60 bits total
 *   - Split as 20 bits lat + 20 bits lon + 20 bits alt
 *   - Interleave order per bit position i (0-indexed from MSB):
 *       i%3 === 0 → lat bit
 *       i%3 === 1 → lon bit
 *       i%3 === 2 → alt bit
 *   - lat range : -90  to  90
 *   - lon range : -180 to  180
 *   - alt range : -500 to  8500  (9000 m total)
 */

const BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz';
const BASE32_MAP = {};
for (let i = 0; i < BASE32.length; i++) BASE32_MAP[BASE32[i]] = i;

const LAT_MIN = -90,  LAT_MAX =  90;
const LON_MIN = -180, LON_MAX =  180;
const ALT_MIN = -500, ALT_MAX =  8500;
const BITS = 20; // bits per dimension
const PRECISION = 12; // chars

/**
 * Normalize a value in [min, max] to an integer in [0, 2^bits - 1]
 */
function normToInt(val, min, max, bits) {
  const range = max - min;
  const norm = (val - min) / range;
  const maxInt = (1 << bits) >>> 0; // 2^bits as unsigned
  // clamp
  const clamped = Math.max(0, Math.min(1 - Number.EPSILON, norm));
  return Math.floor(clamped * maxInt);
}

/**
 * Convert an integer back to coordinate value (center of cell)
 */
function intToVal(intVal, min, max, bits) {
  const maxInt = (1 << bits) >>> 0;
  const cellSize = (max - min) / maxInt;
  return min + (intVal + 0.5) * cellSize;
}

/**
 * Encode lat, lon, alt into a 12-character Base32 3D geohash string.
 * @param {number} lat  latitude  in [-90, 90]
 * @param {number} lon  longitude in [-180, 180]
 * @param {number} alt  altitude  in [-500, 8500]  (metres)
 * @param {number} precision  number of chars (default 12)
 * @returns {string} 12-char Base32 geohash
 */
export function encode(lat, lon, alt = 0, precision = PRECISION) {
  const latInt = normToInt(lat, LAT_MIN, LAT_MAX, BITS);
  const lonInt = normToInt(lon, LON_MIN, LON_MAX, BITS);
  const altInt = normToInt(alt, ALT_MIN, ALT_MAX, BITS);

  // Total bits = precision * 5
  const totalBits = precision * 5;
  // We use 20 bits per dimension; fill MSB-first
  // bit position i (0 = MSB of output):
  //   component = i % 3: 0→lat, 1→lon, 2→alt
  //   within-component bit index:
  //     lat gets bits at positions 0,3,6,...  → latBitIdx = floor(i/3)
  //     lon gets bits at positions 1,4,7,...  → lonBitIdx = floor(i/3)
  //     alt gets bits at positions 2,5,8,...  → altBitIdx = floor(i/3)
  // Since totalBits = 60 and BITS = 20, each dimension gets exactly 20 bits.

  let chars = '';
  let acc = 0;
  let accBits = 0;

  for (let i = 0; i < totalBits; i++) {
    const dim = i % 3; // 0=lat, 1=lon, 2=alt
    const dimBitIdx = Math.floor(i / 3); // 0..19 (MSB first within dimension)
    const bitFromMSB = BITS - 1 - dimBitIdx; // bit position in integer (0=LSB)

    let intVal;
    if (dim === 0) intVal = latInt;
    else if (dim === 1) intVal = lonInt;
    else intVal = altInt;

    const bit = (intVal >>> bitFromMSB) & 1;
    acc = (acc << 1) | bit;
    accBits++;

    if (accBits === 5) {
      chars += BASE32[acc];
      acc = 0;
      accBits = 0;
    }
  }

  return chars;
}

/**
 * Decode a 3D geohash string into {lat, lon, alt, error: {lat, lon, alt}}
 * Returns center of cell + error (half cell size per dimension).
 * @param {string} hash  Base32 geohash string (up to 12 chars)
 * @returns {{lat:number, lon:number, alt:number, error:{lat:number,lon:number,alt:number}}}
 */
export function decode(hash) {
  const bounds = toBounds(hash);
  return {
    lat: (bounds.minLat + bounds.maxLat) / 2,
    lon: (bounds.minLon + bounds.maxLon) / 2,
    alt: (bounds.minAlt + bounds.maxAlt) / 2,
    error: {
      lat: (bounds.maxLat - bounds.minLat) / 2,
      lon: (bounds.maxLon - bounds.minLon) / 2,
      alt: (bounds.maxAlt - bounds.minAlt) / 2,
    },
  };
}

/**
 * Return the bounding box of a 3D geohash.
 * @param {string} hash  Base32 geohash string
 * @returns {{minLat,maxLat,minLon,maxLon,minAlt,maxAlt}}
 */
export function toBounds(hash) {
  const len = hash.length;
  const totalBits = len * 5;

  // Determine how many bits each dimension gets
  // bit positions 0,3,6,... → lat; 1,4,7,... → lon; 2,5,8,... → alt
  let latBits = 0, lonBits = 0, altBits = 0;
  for (let i = 0; i < totalBits; i++) {
    const dim = i % 3;
    if (dim === 0) latBits++;
    else if (dim === 1) lonBits++;
    else altBits++;
  }

  // Reconstruct per-dimension integer values from the hash bits
  let latInt = 0, lonInt = 0, altInt = 0;

  for (let i = 0; i < totalBits; i++) {
    const charIdx = Math.floor(i / 5);
    const bitInChar = 4 - (i % 5); // MSB first within char
    const charVal = BASE32_MAP[hash[charIdx]];
    if (charVal === undefined) throw new Error(`Invalid Base32 character: '${hash[charIdx]}'`);
    const bit = (charVal >>> bitInChar) & 1;

    const dim = i % 3;
    const dimBitIdx = Math.floor(i / 3); // which bit within dimension (MSB first)

    if (dim === 0) {
      latInt = (latInt << 1) | bit;
    } else if (dim === 1) {
      lonInt = (lonInt << 1) | bit;
    } else {
      altInt = (altInt << 1) | bit;
    }
  }

  // Convert integer ranges to coordinate bounds
  const latRange = LAT_MAX - LAT_MIN;
  const lonRange = LON_MAX - LON_MIN;
  const altRange = ALT_MAX - ALT_MIN;

  const latMaxInt = (1 << latBits) >>> 0;
  const lonMaxInt = (1 << lonBits) >>> 0;
  const altMaxInt = (1 << altBits) >>> 0;

  const latCellSize = latRange / latMaxInt;
  const lonCellSize = lonRange / lonMaxInt;
  const altCellSize = altRange / altMaxInt;

  const minLat = LAT_MIN + latInt * latCellSize;
  const minLon = LON_MIN + lonInt * lonCellSize;
  const minAlt = ALT_MIN + altInt * altCellSize;

  return {
    minLat,
    maxLat: minLat + latCellSize,
    minLon,
    maxLon: minLon + lonCellSize,
    minAlt,
    maxAlt: minAlt + altCellSize,
  };
}

// ---------------------------------------------------------------------------
// Self-test (uncomment to run in browser console or Node.js)
// ---------------------------------------------------------------------------
// function selfTest() {
//   const tests = [
//     { lat: 55.6761,  lon: 12.5683,  alt: 10,   desc: 'Copenhagen' },
//     { lat: 51.5074,  lon: -0.1278,  alt: 11,   desc: 'London' },
//     { lat: 40.7128,  lon: -74.0060, alt: 10,   desc: 'New York' },
//     { lat: 35.6762,  lon: 139.6503, alt: 40,   desc: 'Tokyo' },
//     { lat: -33.8688, lon: 151.2093, alt: 50,   desc: 'Sydney' },
//     { lat: 0,        lon: 0,        alt: 0,    desc: 'Null Island' },
//     { lat: -90,      lon: -180,     alt: -500, desc: 'Min corner' },
//     { lat: 89.9999,  lon: 179.9999, alt: 8499, desc: 'Near max corner' },
//     { lat: 55.6761,  lon: 12.5683,  alt: 0,    desc: 'Copenhagen alt=0' },
//   ];
//
//   console.log('=== geohash3d self-test ===');
//   let pass = 0, fail = 0;
//
//   for (const t of tests) {
//     const hash = encode(t.lat, t.lon, t.alt);
//     const result = decode(hash);
//     const latOk = Math.abs(result.lat - t.lat) <= result.error.lat;
//     const lonOk = Math.abs(result.lon - t.lon) <= result.error.lon;
//     const altOk = Math.abs(result.alt - t.alt) <= result.error.alt;
//     const ok = latOk && lonOk && altOk;
//     if (ok) pass++; else fail++;
//     console.log(
//       `${ok ? 'PASS' : 'FAIL'} ${t.desc}: hash=${hash}`,
//       `decoded=(${result.lat.toFixed(4)}, ${result.lon.toFixed(4)}, ${result.alt.toFixed(1)})`,
//       `err=(±${result.error.lat.toFixed(4)}, ±${result.error.lon.toFixed(4)}, ±${result.error.alt.toFixed(1)})`,
//     );
//   }
//
//   // Round-trip precision test at 12 chars
//   const h12 = encode(55.6761, 12.5683, 42);
//   const d12 = decode(h12);
//   console.log(`\n12-char precision: lat_err=±${d12.error.lat.toFixed(6)}°, lon_err=±${d12.error.lon.toFixed(6)}°, alt_err=±${d12.error.alt.toFixed(2)}m`);
//
//   console.log(`\nResults: ${pass} passed, ${fail} failed`);
// }
// selfTest();
