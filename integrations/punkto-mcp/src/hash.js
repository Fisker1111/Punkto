// Adapter-local formatting only. Canonical MID computation remains in carrier.js.
const HEX = '0123456789abcdef';
export function hex(bytes) {
  let result = '';
  for (let i = 0; i < bytes.length; i++) {
    const byte = bytes[i];
    result += HEX[byte >>> 4] + HEX[byte & 15];
  }
  return result;
}
export async function sha256Hex(bytes) {
  return hex(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)));
}
