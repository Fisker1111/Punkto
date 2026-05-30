/**
 * Relay-compatible atom id helpers.
 * Mirrors relay canonical_bytes(): sorted JSON keys, no whitespace, UTF-8,
 * excluding the optional signature field.
 */

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value)
      .filter((key) => key !== 'sig' && value[key] !== undefined)
      .sort()
      .map((key) => JSON.stringify(key) + ':' + stableJson(value[key]))
      .join(',') + '}';
  }
  return JSON.stringify(value);
}

function bytesToHex(buffer) {
  return Array.from(new Uint8Array(buffer), (b) => b.toString(16).padStart(2, '0')).join('');
}

function getCrypto() {
  if (globalThis.crypto?.subtle) return globalThis.crypto;
  return null;
}

export async function computeAtomId(atom) {
  const cryptoImpl = getCrypto();
  if (!cryptoImpl) throw new Error('Web Crypto is unavailable');
  const canonical = stableJson(atom && typeof atom === 'object' ? atom : {});
  const data = new TextEncoder().encode(canonical);
  const digest = await cryptoImpl.subtle.digest('SHA-256', data);
  return bytesToHex(digest);
}

export function isStableAtomId(value) {
  return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
}
