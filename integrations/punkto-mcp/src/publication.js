import { parse_h, xy_key } from '../../../pwa/punkti/spatial.js';
import { fail, digest, withOrigin } from './upstream.js';
import { metadata, b64, trust } from './records.js';
const decoder = new TextDecoder('utf-8', { fatal: true });
const DEFAULT_H = 's00000000000_0';
function reference(value) {
  try { return digest(value); } catch { fail('corrupt_object', 'Invalid publication digest reference.'); }
}
function json(bytes) {
  try { const value = JSON.parse(decoder.decode(bytes)); if (value && typeof value === 'object' && !Array.isArray(value)) return value; } catch { /* Typed below. */ }
  fail('corrupt_object', 'Invalid publication JSON object.');
}
export async function readPlace({ h = DEFAULT_H, limit = 4 } = {}, options) {
  let xy;
  try { xy = parse_h(h).xy; } catch { fail('invalid_h', 'Supply a canonical Punkti xy_z address.'); }
  if (!Number.isInteger(limit) || limit < 1) fail('invalid_h', 'limit must be an integer of at least 1.');
  const clamped = limit > 8;
  limit = Math.min(limit, 8);
  const leaf = xy_key(xy).slice(0, 10);
  return withOrigin(async client => {
    const root = json(await client.get('root'));
    reference(root.head);
    if (root.v !== 'punkti/pub/0.6' || !Number.isSafeInteger(root.seq) || root.seq < 1) fail('corrupt_object', 'Invalid publication root.');
    const manifest = json(await client.get('manifest', root.head));
    if (manifest.v !== root.v || manifest.seq !== root.seq || !manifest.index || typeof manifest.index !== 'object' || Array.isArray(manifest.index)) fail('corrupt_object', 'Invalid publication manifest.');
    let prefix = leaf.slice(0, 2);
    let sha = manifest.index?.[prefix];
    if (!sha) fail('not_found_in_publication', 'Address absent from this published snapshot.');
    let shard;
    while (prefix.length <= 10) {
      shard = json(await client.get('shard', reference(sha), prefix));
      if (shard.v !== root.v || shard.prefix !== prefix) fail('corrupt_object', 'Shard prefix differs from its reference.');
      if (prefix.length === 10) break;
      prefix = leaf.slice(0, prefix.length + 1);
      sha = shard.children?.[prefix];
      if (!sha) fail('not_found_in_publication', 'Address absent from this published snapshot.');
    }
    if (!Array.isArray(shard.records)) fail('corrupt_object', 'Leaf records are missing.');
    const entries = shard.records.filter(entry => entry.h === h).slice(0, limit);
    if (!entries.length) fail('not_found_in_publication', 'Exact address absent from this published snapshot.');
    const records = [];
    for (const entry of entries) {
      const bytes = await client.get('record', reference(entry.sha256));
      const decoded = await metadata(bytes);
      records.push({ h: entry.h, mid: entry.mid, ...decoded,
        ...(decoded.mid && decoded.mid !== entry.mid ? { mid_matches_leaf: false } : {}),
        record_sha256: entry.sha256, record_url: client.url('record', entry.sha256), record_bytes: bytes.length });
    }
    return { h, records, publication_root: root.head, root_seq: root.seq, publication_head: root.head,
      root_verification: 'unverified-by-digest', snapshot_note: "one node's published view; not a completeness or persistence claim",
      ...(clamped ? { limit_note: 'limit clamped to 8' } : {}), ...trust };
  }, options);
}
export async function getRecord({ sha256, include_raw = false } = {}, options) {
  if (typeof sha256 === 'string' && /^punkti\/[^:]+:/.test(sha256)) fail('use_sha256_not_mid', 'Use the record SHA-256; a MID has no direct static record URL.');
  digest(sha256);
  if (typeof include_raw !== 'boolean') fail('invalid_sha256', 'include_raw must be a boolean.');
  return withOrigin(async client => {
    const bytes = await client.get('record', sha256, undefined, 'digest_mismatch');
    if (include_raw && bytes.length > 32768) fail('record_too_large', `Download ${client.url('record', sha256)} and verify its digest locally.`);
    return { sha256, record_url: client.url('record', sha256), record_bytes: bytes.length,
      ...await metadata(bytes), ...(include_raw ? { record_base64: b64(bytes) } : {}), ...trust };
  }, options);
}
