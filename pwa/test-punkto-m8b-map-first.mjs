import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { initialPageForBoot, EXPLORE_PLACE_LIMIT, selectExplorePlaces, primaryExplorePlace, explorePlacesHtml, exploreNudgeBodyHtml } from './core/explore.js';
import { mapRecordToAtom } from './sync/punkti-client.js';
import { escHtml } from './core/display.js';
import { isQaRecord } from './core/read-state.js';
import { resolveBoardAtom, boardReplies } from './ui-text.js';
import { shouldDeferViewportPadding } from './ui-map.js';

const fixture = JSON.parse(await readFile(new URL('./tests/publication-live-60.json', import.meta.url), 'utf8'));
const atoms = fixture.records.map(({ mid, sha256, h, x, refs, t, pk, sig }) =>
  mapRecordToAtom({ mid, sha256, h, atom: { x, refs, t, pk, sig } }, fixture.publication));
const index = await readFile(new URL('./index.html', import.meta.url), 'utf8');
let passed = 0;
function check(name, run) {
  run();
  passed++;
  console.log(`PASS ${name}`);
}
const places = selectExplorePlaces(atoms);

check('ordinary and deep-link visitors start on Map', () => {
  assert.equal(initialPageForBoot(), 'map');
  assert.equal(initialPageForBoot('/p/example'), 'map');
});
check('real publication offers only the genuine exact-address place deterministically', () => {
  const snapshot = structuredClone(atoms);
  assert.equal(places.length, 1);
  assert.equal(places[0].h, 's00000000000_0');
  assert.equal(places[0].kind, 'public');
  assert.ok(places.length <= EXPLORE_PLACE_LIMIT);
  for (const place of places) {
    assert.notEqual(place.kind, 'qa');
    assert.ok(atoms.some(atom => atom.h === place.h && !isQaRecord(atom)));
    assert.ok(place.h && Number.isFinite(place.lat) && Number.isFinite(place.lon));
    assert.equal(place.atomId, atoms.find(atom => atom.h === place.h && atom.relation !== 'reply' && !atom.parent_id).atom_id);
  }
  assert.deepEqual(selectExplorePlaces(atoms), places);
  assert.deepEqual(atoms, snapshot);
  assert.equal(primaryExplorePlace(places), places[0]);
  assert.equal(primaryExplorePlace([]), null);
});
check('offered board and both real replies resolve through the existing exact-address threads', () => {
  const replies = atoms.filter(atom => atom.relation === 'reply');
  assert.equal(replies.length, 2);
  for (const reply of replies) {
    const root = atoms.find(atom => atom.atom_id === reply.parent_id);
    assert.equal(resolveBoardAtom(reply, atoms), root);
    assert.equal(root.h, reply.h);
    assert.deepEqual(boardReplies(root, atoms), [reply]);
  }
  const offered = atoms.find(atom => atom.atom_id === places[0].atomId);
  const board = resolveBoardAtom(offered, atoms);
  assert.equal(board, offered);
  assert.deepEqual(boardReplies(board, atoms), replies.filter(reply => reply.parent_id === offered.atom_id));
  assert.equal(boardReplies(board, atoms).length, 1);
});
check('rendered places contain only source titles, exact addresses and accessible buttons', () => {
  const html = explorePlacesHtml(places);
  assert.doesNotMatch(html, /verified|likes?|followers?/i);
  assert.equal((html.match(/<button\b/g) || []).length, places.length);
  for (const place of places) {
    assert.ok(html.includes(`data-atom-id="${place.atomId}"`));
    assert.ok(html.replaceAll("&#39;", "'").includes(escHtml(place.title)));
    assert.ok(html.includes(place.h));
    assert.equal(place.title, atoms.find(atom => atom.atom_id === place.atomId).x.split('\n')[0]);
  }
  for (const button of html.match(/<button\b[^>]*>/g)) {
    assert.match(button, /type="button"/);
    assert.match(button, /data-action="explore-place"/);
    assert.match(button, /class="[^"]*explore-place-button/);
  }
  assert.match(index, /\.explore-place-button\s*\{[^}]*min-height:\s*44px/);
  assert.match(index, /id="map-explore-nudge"[^>]*aria-label="Explore a real place"[^>]*aria-live="polite"/);
  assert.doesNotMatch(index, /first-visit-explore|Explore published text/);
});
check('known places survive background resyncs while empty states stay honest', () => {
  for (const state of ['loading', 'syncing', 'error', 'ok']) {
    const html = exploreNudgeBodyHtml(places, state);
    assert.ok(html.includes(`data-atom-id="${places[0].atomId}"`));
    assert.doesNotMatch(html, /Loading published places…/);
    assert.equal((html.match(/<button\b[^>]*data-action="explore-place"/g) || []).length, 1);
    assert.equal(html, explorePlacesHtml(places));
  }
  const loading = exploreNudgeBodyHtml([], 'loading');
  assert.match(loading, /Loading published places…/);
  assert.doesNotMatch(loading, /<button\b[^>]*data-action="explore-place"/);
  const error = exploreNudgeBodyHtml([], 'error');
  assert.match(error, /Could not load published places\. Try again\./);
  assert.match(error, /<button\b[^>]*data-action="retry-read"/);
  assert.match(exploreNudgeBodyHtml([], 'ok'), /No published places in this scope\./);
});
check('QA-only fallback stays labelled and sorted, and respects limits', () => {
  const qa = atoms.filter(isQaRecord);
  const fallback = selectExplorePlaces(qa);
  assert.equal(fallback.length, EXPLORE_PLACE_LIMIT);
  assert.ok(fallback.every(place => place.kind === 'qa'));
  assert.equal((explorePlacesHtml(fallback).match(/QA record/g) || []).length, fallback.length);
  assert.deepEqual(selectExplorePlaces(qa, { limit: 1 }), fallback.slice(0, 1));
  assert.deepEqual(selectExplorePlaces(qa, { limit: 0 }), []);
  const roots = qa.filter(atom => atom.relation !== 'reply' && !atom.parent_id);
  const groups = [...new Set(roots.map(atom => atom.h))];
  groups.sort((a, b) => roots.filter(atom => atom.h === b).length - roots.filter(atom => atom.h === a).length || (a < b ? -1 : a > b ? 1 : 0));
  assert.deepEqual(fallback.map(place => place.h), groups.slice(0, EXPLORE_PLACE_LIMIT));
});
check('reply-only and invalid-position inputs never invent a place; mixed groups preserve first root', () => {
  assert.deepEqual(selectExplorePlaces(atoms.filter(atom => atom.relation === 'reply')), []);
  const root = atoms.find(atom => atom.atom_id === places[0].atomId);
  for (const patch of [{ h: '' }, { lat: NaN }, { lon: Infinity }, { parent_id: root.atom_id }]) {
    assert.deepEqual(selectExplorePlaces([{ ...root, ...patch }]), []);
  }
  const qaRoot = atoms.find(atom => isQaRecord(atom) && !atom.parent_id);
  const mixed = selectExplorePlaces([{ ...qaRoot, h: root.h }, root]);
  assert.equal(mixed[0].kind, 'public');
  assert.equal(mixed[0].atomId, qaRoot.atom_id);
  const escaped = explorePlacesHtml([{ ...places[0], title: '<script>"&', atomId: '" onclick="bad' }]);
  assert.doesNotMatch(escaped, /<script>|data-atom-id=""/);
  assert.match(escaped, /&lt;script&gt;&quot;&amp;/);
});

check('viewport padding defers only while the camera reports motion, with safe fallbacks', () => {
  assert.equal(shouldDeferViewportPadding({ isMoving: () => true }), true);
  assert.equal(shouldDeferViewportPadding({ isMoving: () => false }), false);
  assert.equal(shouldDeferViewportPadding({}), false);
  assert.equal(shouldDeferViewportPadding({ isMoving() { throw new Error('unavailable'); } }), false);
  assert.equal(shouldDeferViewportPadding(null), false);
  assert.equal(shouldDeferViewportPadding(undefined), false);
});

check('mobile board sheet clears the nav footprint while the desktop offset stays unchanged', () => {
  const sheet = index.match(/#map-board-sheet\s*\{([^}]*)\}/);
  assert.ok(sheet, 'default map board sheet rule exists');
  assert.match(sheet[1], /(?:^|;)\s*bottom\s*:\s*calc\(\s*134px\s*\+\s*var\(\s*--safe-b\s*\)\s*\)\s*;/);
  assert.match(index, /@media\s*\(\s*max-width\s*:\s*899px\s*\)\s*\{\s*:root\s*\{\s*--nav-h\s*:\s*134px\s*;\s*\}/);
  assert.match(index, /@media\s*\(\s*min-width\s*:\s*900px\s*\)\s*\{\s*#map-board-sheet\s*\{[^}]*\bbottom\s*:\s*20px\s*;/);
});

console.log(`${passed}/${passed} M8B map-first checks passed (initial Map, real explore place, exact-address board).`);
