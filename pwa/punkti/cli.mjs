import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { webcrypto } from 'node:crypto';
import { VERSION } from './carrier.js';
import { encode_h, parse_h, xy_key } from './spatial.js';
import { createReader } from './reader.js';
import { createSubmitClient } from './submit.js';

const require = createRequire(import.meta.url);
try { globalThis.nacl = require('./nacl.min.js'); }
catch { globalThis.nacl = require('../nacl.min.js'); }
globalThis.crypto ??= webcrypto;

const alphabet = '0123456789bcdefghjkmnpqrstuvwxyz';
function scopeFor(options) {
  const scope = {};
  if (options.xy !== undefined) {
    xy_key(options.xy);
    scope.xy_lo = options.xy;
    let chars = [...options.xy];
    while (chars.length && chars.at(-1) === 'z') chars.pop();
    if (chars.length) {
      chars[chars.length - 1] = alphabet[alphabet.indexOf(chars.at(-1)) + 1];
      scope.xy_hi = chars.join('');
    }
  }
  if (options['z-min'] !== undefined) scope.z_min = options['z-min'];
  if (options['z-max'] !== undefined) scope.z_max = options['z-max'];
  return scope;
}
function url(value) {
  const parsed = new URL(value);
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('http(s) URL required');
  return value;
}
export async function run(args, fetchImpl = globalThis.fetch) {
  const [command, ...flags] = args;
  if (!['read', 'write', 'reply'].includes(command)) throw new Error('expected read, write or reply');
  const allowed = new Set(['nodes', ...(command === 'read' ? ['publication', 'xy', 'z-min', 'z-max', 'limit'] : ['submit', 'text', 'lat', 'lon', 'height', 'h', ...(command === 'reply' ? ['ref'] : [])])]);
  const options = {};
  for (let i = 0; i < flags.length; i += 2) {
    const key = flags[i].slice(2);
    if (!flags[i].startsWith('--') || !allowed.has(key) || flags[i + 1] === undefined || Object.hasOwn(options, key)) throw new Error('invalid or repeated option');
    options[key] = flags[i + 1];
  }
  if (!options.nodes) throw new Error('--nodes URL required');
  const timedFetch = (address, init = {}) => fetchImpl(address, { ...init, signal: AbortSignal.timeout(5000) });
  const response = await timedFetch(url(options.nodes));
  if (!response.ok) throw new Error(`bootstrap HTTP ${response.status}`);
  const bootstrap = await response.json();
  if (bootstrap.v !== 'punkti/bootstrap/1' || !Array.isArray(bootstrap.nodes) || !bootstrap.nodes.length) throw new Error('bootstrap has no nodes');
  const node = bootstrap.nodes[0];
  if (command === 'read') {
    const limit = options.limit === undefined ? Infinity : Number(options.limit);
    if (options.limit !== undefined && (!Number.isSafeInteger(limit) || limit < 0)) throw new Error('invalid limit');
    const base = url(options.publication ?? node.publication);
    const result = await createReader({ fetchImpl: timedFetch, maxRetries: 0 }).readPublication(base, scopeFor(options));
    return {
      publication: { url: base, head: result.head, seq: result.seq, valid: result.valid_count, candidates: result.candidate_count, rejected: result.rejected },
      records: result.records.slice(0, limit).map(({ mid, h, state, atom }) => {
        let text = atom.x;
        try { text = JSON.parse(atom.x).text ?? atom.x; } catch {}
        return { mid, h, state, text };
      }),
    };
  }
  if (!node.submit) throw new Error('selected node does not accept writes (no submit entry)');
  const submitUrl = url(options.submit ?? node.submit);
  if (options.text === undefined) throw new Error('--text required');
  if (command === 'reply' && !/^punkti\/0\.6:[0-9a-f]{64}$/.test(options.ref ?? '')) throw new Error('invalid MID reference');
  let h = '';
  const hasCoords = options.lat !== undefined || options.lon !== undefined || options.height !== undefined;
  if (options.h !== undefined && hasCoords) throw new Error('choose --h or coordinates');
  if (options.h !== undefined) { parse_h(options.h); h = options.h; }
  else if (hasCoords) {
    if (options.lat === undefined || options.lon === undefined || options.lat.trim() === '' || options.lon.trim() === '') throw new Error('--lat and --lon required');
    if (options.height !== undefined && options.height.trim() === '') throw new Error('height required');
    h = encode_h(Number(options.lat), Number(options.lon), options.height === undefined ? 0 : Number(options.height));
  }
  const identity = globalThis.nacl.sign.keyPair();
  const client = createSubmitClient({
    baseUrl: node.base,
    identity,
    // The frozen client constructs /submit; route its sole HTTP request to the
    // operator-selected endpoint, including endpoints with custom paths.
    fetchImpl: (_address, init) => timedFetch(submitUrl, init),
  });
  const result = await client.submit({ v: VERSION, t: Date.now(), h, x: JSON.stringify({ text: options.text }), alg: 'ed25519', refs: command === 'reply' ? [{ target: options.ref, rel: 'reply' }] : [], ext: '' });
  if (!result.ok) throw new Error(result.error);
  return command === 'reply' ? { mid: result.mid, ref: options.ref } : { mid: result.mid, sha256: result.sha256, duplicate: result.duplicate };
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { console.log(JSON.stringify(await run(process.argv.slice(2)))); }
  catch (error) { console.log(JSON.stringify({ error: error.message })); process.exitCode = 1; }
}
