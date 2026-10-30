import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { webcrypto, randomBytes, createHash } from 'node:crypto';
import { readFile, writeFile, realpath } from 'node:fs/promises';
import path from 'node:path';
import { VERSION, decodeRecord, computeMid, signingInput, unb64 } from '../punkti/carrier.js';
import { parse_h, encode_h, xy_key } from '../punkti/spatial.js';
import { createReader } from '../punkti/reader.js';
import { createSubmitClient } from '../punkti/submit.js';

const require = createRequire(import.meta.url);
try { globalThis.nacl = require('./nacl.min.js'); }
catch { globalThis.nacl = require('../nacl.min.js'); }
globalThis.crypto ??= webcrypto;
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const midPattern = /^punkti\/0\.6:[0-9a-f]{64}$/;
const notice = 'starting point, not a trust authority, not a completeness claim';
const usage = `Usage: node agent.mjs boot|discover|publish|verify|reply --nodes <nodes.json URL>
 discover [--xy <prefix>] [--limit N]
 publish (--h <xy>_<z> | --lat <lat> --lon <lon> --height <ellipsoidal metres>) --text <text> [--key-file <path>]
 verify --mid <punkti/0.6:hex> [--h <xy>_<z>]
 reply --parent-mid <mid> --text <text> [--key-file <path>]
 boot defaults to http://127.0.0.1:8000/nodes.json. First advertised node is selected.
 All requests are summarized on stderr; JSON results go to stdout.`;

function spatial(h) {
  try { if (parse_h(h)) return h; } catch {}
  throw new Error('explicit canonical XY_Z required (lowercase GeoHash 4–12 chars, exact canonical ellipsoidal Z); never guess Z');
}
function optionsFor(args) {
  const [command, ...flags] = args;
  const allowed = { boot: [], discover: ['xy', 'limit'], publish: ['h', 'lat', 'lon', 'height', 'text', 'key-file'], verify: ['mid', 'h'], reply: ['parent-mid', 'text', 'key-file', 'h'] };
  if (!Object.hasOwn(allowed, command)) throw new Error(usage);
  const options = {};
  for (let i = 0; i < flags.length; i++) {
    const match = /^--([^=]+)(?:=(.*))?$/.exec(flags[i]);
    if (!match) throw new Error('expected --option value');
    const [, key, inline] = match;
    if (!['nodes', ...allowed[command]].includes(key) || Object.hasOwn(options, key)) throw new Error(`unknown or repeated option --${key}`);
    const value = inline ?? flags[++i];
    if (value === undefined || value.startsWith('--')) throw new Error(`missing value --${key}`);
    options[key] = value;
  }
  return { command, options };
}
function checkedURL(value) {
  const u = new URL(value);
  if (!['http:', 'https:'].includes(u.protocol) || u.username || u.password || u.hash) throw new Error('plain http(s) URL required');
  if (process.env.PUNKTO_LOCAL_ONLY === '1' && u.hostname !== '127.0.0.1') throw new Error('Stage 0 permits only 127.0.0.1 requests');
  return u.href;
}
async function identity(keyFile) {
  if (!keyFile) return { pair: nacl.sign.keyPair(), mode: 'ephemeral: no continuity across invocations' };
  const parent = await realpath(path.dirname(path.resolve(keyFile)));
  const target = path.join(parent, path.basename(keyFile));
  // Find a checkout ancestor without reading any repository content.
  let ancestor = path.dirname(fileURLToPath(import.meta.url));
  while (ancestor !== path.dirname(ancestor)) {
    try {
      await realpath(path.join(ancestor, '.git'));
      if (target === ancestor || target.startsWith(ancestor + path.sep)) throw new Error('key files must be outside the repository');
      break;
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
    ancestor = path.dirname(ancestor);
  }
  try { await writeFile(target, randomBytes(32).toString('hex') + '\n', { mode: 0o600, flag: 'wx' }); }
  catch (error) { if (error.code !== 'EEXIST') throw error; }
  const seed = (await readFile(target, 'utf8')).trim();
  if (!/^[0-9a-f]{64}$/.test(seed)) throw new Error('key file must contain a 32-byte lowercase hex seed');
  return { pair: nacl.sign.keyPair.fromSeed(Buffer.from(seed, 'hex')), mode: 'reusable key: stable public-key continuity' };
}

export async function run(args) {
  if (!args.length || args[0] === '--help') return { usage };
  const { command, options: o } = optionsFor(args);
  let h;
  if (command === 'publish') {
    const coords = ['lat', 'lon', 'height'].some(k => o[k] !== undefined);
    if (o.h !== undefined && coords) throw new Error('choose --h or all three coordinates');
    if (o.h !== undefined) h = spatial(o.h);
    else {
      if (!['lat', 'lon', 'height'].every(k => o[k]?.trim())) throw new Error('explicit --h or --lat/--lon/--height required; never guess Z');
      // Preserve exact decimal height rather than round-tripping through a float.
      h = spatial(encode_h(Number(o.lat), Number(o.lon), o.height));
    }
  }
  if (['publish', 'reply'].includes(command) && o.text === undefined) throw new Error('--text required');
  if (command === 'verify' && !midPattern.test(o.mid ?? '')) throw new Error('valid --mid required');
  if (command === 'reply' && !midPattern.test(o['parent-mid'] ?? '')) throw new Error('valid --parent-mid required');
  if (o.h !== undefined) spatial(o.h);
  if (o.xy !== undefined) xy_key(o.xy);
  const limit = o.limit === undefined ? Infinity : Number(o.limit);
  if (o.limit !== undefined && (!Number.isSafeInteger(limit) || limit < 0)) throw new Error('limit must be a nonnegative integer');
  const entries = new Map();
  const http = async (url, init = {}) => {
    const response = await fetch(checkedURL(url), { ...init, redirect: 'error', signal: AbortSignal.timeout(10000) });
    const bytes = Buffer.from(await response.clone().arrayBuffer());
    const digest = /\/(?:([0-9a-f]{64})\.json|([0-9a-f]{64}))$/.exec(new URL(url).pathname);
    const sha = hash(bytes);
    console.error(`HTTP ${init.method ?? 'GET'} ${url} -> ${response.status} bytes=${bytes.length}${digest ? ` sha256=${sha}` : ''}`);
    if (response.ok && digest && sha !== (digest[1] ?? digest[2])) throw new Error(`SHA-256 FAIL: immutable object mismatch at ${url}`);
    if (response.ok && new URL(url).pathname.includes('/h/')) {
      for (const entry of JSON.parse(bytes).records ?? []) entries.set(entry.sha256, entry);
    }
    return response;
  };
  const response = await http(o.nodes ?? (command === 'boot' ? 'http://127.0.0.1:8000/nodes.json' : (() => { throw new Error('--nodes URL required'); })()));
  if (!response.ok) throw new Error(`bootstrap HTTP ${response.status}`);
  const bootstrap = await response.json();
  if (bootstrap.v !== 'punkti/bootstrap/1' || !Array.isArray(bootstrap.nodes) || !bootstrap.nodes.length) throw new Error('invalid bootstrap version or empty nodes');
  for (const n of bootstrap.nodes) {
    if (typeof n.id !== 'string' || !n.id) throw new Error('node id required');
    checkedURL(n.base); checkedURL(n.publication); if (n.submit) checkedURL(n.submit);
  }
  if (command === 'boot') return { notice, nodes: bootstrap.nodes };
  const node = bootstrap.nodes[0];
  const reader = createReader({ fetchImpl: http, maxRetries: 0 });
  const read = async () => {
    try { return await reader.readPublication(node.publication); }
    catch (error) { throw new Error(`static publication verification FAIL: ${error.message} (corrupt object means SHA-256 mismatch)`); }
  };
  const verify = async (mid, expectedH) => {
    const publication = await read();
    const entry = [...entries.values()].find(e => e.mid === mid);
    if (!entry) return { visible: false, mid, head: publication.head, seq: publication.seq, message: 'not yet visible in latest static publication (publication lag or absent from this node view)' };
    const raw = await reader.readRecord(node.publication, entry.sha256);
    const checks = { sha256: hash(raw) === entry.sha256 ? 'PASS' : 'FAIL', mid: 'FAIL', signature: 'FAIL', h: 'FAIL' };
    let atom;
    try {
      const decoded = decodeRecord(raw); atom = decoded.atom;
      checks.mid = `${VERSION}:${await computeMid(decoded.body)}` === mid ? 'PASS' : 'FAIL';
      checks.signature = atom.alg === 'ed25519' && nacl.sign.detached.verify(signingInput(decoded.body), decoded.sig, unb64(atom.pk)) ? 'PASS' : 'FAIL';
      checks.h = spatial(atom.h) === entry.h && (expectedH === undefined || atom.h === expectedH) ? 'PASS' : 'FAIL';
    } catch {}
    return { visible: true, ok: Object.values(checks).every(v => v === 'PASS'), checks, mid, sha256: hash(raw), h: atom?.h, publicKey: atom?.pk, refs: atom?.refs, head: publication.head, seq: publication.seq };
  };
  if (command === 'discover') {
    const publication = await read();
    const selected = [...entries.values()].filter(e => e.h && parse_h(e.h)?.xy.startsWith(o.xy ?? ''));
    const branches = {};
    for (const e of selected) {
      const xy = parse_h(e.h).xy;
      for (let length = 1; length <= xy.length; length++) {
        const prefix = xy.slice(0, length);
        branches[prefix] = (branches[prefix] ?? 0) + 1;
      }
    }
    return { node: node.id, head: publication.head, seq: publication.seq, countsDerived: 'counts of leaf records[] entries in the digest-verified traversed shard tree, grouped by each occupied XY prefix; counts are not truncated by --limit; legacy nonspatial entries excluded', branches, candidates: selected.slice(0, limit), rejected: publication.rejected };
  }
  if (command === 'verify') return verify(o.mid, o.h);
  if (command === 'reply') {
    const parent = await verify(o['parent-mid']);
    if (!parent.visible || !parent.ok) throw new Error(`cannot reply: parent not verified with valid spatial address; ${parent.message ?? JSON.stringify(parent.checks)}`);
    h = spatial(parent.h);
    if (o.h !== undefined && o.h !== h) throw new Error('cross-address references are not replies; reuse parent exact h');
  }
  if (!node.submit) throw new Error('selected node has no submit endpoint');
  const { pair, mode } = await identity(o['key-file']);
  const submitter = createSubmitClient({ baseUrl: node.base, identity: pair, fetchImpl: (_url, init) => http(node.submit, init) });
  const result = await submitter.submit({ v: VERSION, t: Date.now(), h, x: JSON.stringify({ text: o.text }), refs: command === 'reply' ? [{ target: o['parent-mid'], rel: 'reply' }] : [] });
  if (!result.ok || result.state !== 'VALID') throw new Error(`submit rejected: ${result.error ?? result.state}`);
  return { ...result, h, publicKey: Buffer.from(pair.publicKey).toString('base64'), identity: mode, note: 'node accepted the signature; signed acceptance is not proof of visibility. Visible only after the publication writer emits it; re-read static publication to verify.' };
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const result = await run(process.argv.slice(2));
    console.log(JSON.stringify(result));
    if (result.ok === false || result.visible === false) process.exitCode = 1;
  } catch (error) { console.log(JSON.stringify({ error: error.message })); process.exitCode = 1; }
}
