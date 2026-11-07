// Explicit online maintenance / verification command — never a test step.
// Read-only publication GETs; no credentials, redirects, or disk writes.
// Run manually from integrations/punkto-mcp: node scripts/live-m6-check.mjs
import { invoke } from '../src/tools.js';
import catalog from '../src/catalog.json' with { type: 'json' };

let fetches = 0;
async function publicationFetch(address, options) {
  const url = new URL(address);
  if (!['https://punkto.xyz', 'https://test2.punkto.xyz'].includes(url.origin)
    || !url.pathname.startsWith('/publication/') || /%|\.\./.test(url.pathname)
    || url.username || url.password || url.search || url.hash
    || options.method !== 'GET' || options.redirect !== 'manual') {
    throw new Error('Refused non-publication request');
  }
  fetches++;
  return fetch(url, { method: 'GET', redirect: 'manual', credentials: 'omit', signal: options.signal });
}

const options = { fetchImpl: publicationFetch };
const discovery = await invoke('discover_places', {}, options);
if (discovery.isError || fetches !== 0) {
  console.error('FAIL discover_places', discovery.structuredContent, `upstream fetches: ${fetches}`);
  process.exitCode = 1;
} else {
  console.log(`discover_places: structured=${JSON.stringify(discovery.structuredContent).length}, whole=${JSON.stringify(discovery).length}, upstream fetches=${fetches}`);
  let passed = 0;
  for (const place of catalog.places) {
    const read = await invoke('read_place', { h: place.h, limit: 8 }, options);
    if (read.isError) {
      console.error(`FAIL ${place.h}: ${read.structuredContent.code} — ${read.structuredContent.message}`);
      continue;
    }
    const hit = read.structuredContent.records.find(record => record.record_sha256 === place.record_sha256);
    if (!hit) {
      console.error(`FAIL ${place.h}: catalog record SHA-256 absent from live read_place (limit 8)`);
      continue;
    }
    if (hit.mid !== place.mid) {
      console.error(`FAIL ${place.h}: canonical MID mismatch; expected ${place.mid}, received ${hit.mid}`);
      continue;
    }
    passed++;
    console.log(`OK ${place.h}: sha256=${hit.record_sha256} mid=${hit.mid}`);
  }
  console.log(`live-verified places: ${passed}/${catalog.places.length}; upstream fetches: ${fetches}`);
  process.exitCode = passed === catalog.places.length ? 0 : 1;
}
