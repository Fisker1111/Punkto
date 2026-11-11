import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { mapRecordToAtom } from './sync/punkti-client.js';
import { atomsForTextTab, visibleRootCount, isRootAtom, boardReplies } from './ui-text.js';
import { trustLabel, heightLabel, readStateHtml, isQaRecord } from './core/read-state.js';

const fixture = JSON.parse(await readFile(new URL('./tests/publication-live-60.json', import.meta.url), 'utf8'));
// Reconstruct the reader's carrier-record shape, without inventing verification
// results: this decoded snapshot has no reader state field.
const records = fixture.records.map(({ mid, sha256, h, x, refs, t, pk, sig }) => ({
  mid, sha256, h, atom: { x, refs, t, pk, sig },
}));
const atoms = records.map(record => mapRecordToAtom(record, fixture.publication));
assert.equal(atoms.length, 15);
const pairs = [
  ['punkti/0.6:e1865d1e944b23bc2fa3b4c719d8e7dbd0876fd9c185b2539f47edacc20885ca',
    'punkti/0.6:19cf1ba817facbb77fba211af99e7cf456638000e232a94214ac78e2b32b97ad'],
  ['punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854',
    'punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed'],
];
let passed = 0;
function check(name, run) {
  run();
  passed++;
  console.log(`PASS ${name}`);
}

check('real reply refs preserve exact full MIDs; parents and no-ref records stay roots', () => {
  for (const [replyId, parentId] of pairs) {
    const reply = atoms.find(atom => atom.atom_id === replyId);
    const parent = atoms.find(atom => atom.atom_id === parentId);
    assert.ok(reply);
    assert.ok(parent);
    assert.equal(reply.relation, 'reply');
    assert.equal(reply.parent_id, parentId);
    assert.equal(reply.root_id, parentId);
    assert.equal(isRootAtom(parent), true);
    for (const key of ['relation', 'parent_id', 'root_id']) assert.equal(parent[key], undefined);
  }
  for (const record of records.filter(record => !record.atom.refs.length)) {
    const atom = mapRecordToAtom(record);
    for (const key of ['relation', 'parent_id', 'root_id']) assert.equal(atom[key], undefined);
    assert.equal(isRootAtom(atom), true);
  }
});

check('canonical refs win over conflicting payload meta', () => {
  const record = records.find(record => record.mid === pairs[0][0]);
  const conflicting = {
    ...record,
    atom: { ...record.atom, x: JSON.stringify({ text: 'Conflict fixture', meta: {
      relation: 'reply', parent_id: pairs[1][1], root_id: pairs[1][1],
    } }) },
  };
  const atom = mapRecordToAtom(conflicting);
  assert.equal(atom.relation, 'reply');
  assert.equal(atom.parent_id, pairs[0][1]);
  assert.equal(atom.root_id, pairs[0][1]);
});

check('trust labels distinguish verified signatures, unverified signatures, signed and unsigned', () => {
  const verified = trustLabel({ verification_state: 'VALID' });
  assert.match(verified, /Verified/);
  const labels = [verified];
  for (const state of ['INVALID-provenance', 'INVALID-structural', 'UNVERIFIABLE-alg']) {
    const label = trustLabel({ verification_state: state, sig: atoms[0].sig });
    assert.doesNotMatch(label, /Verified/);
    assert.match(label, /signature not verified/i);
    labels.push(label);
  }
  const signed = trustLabel(atoms[0]);
  assert.equal(signed, 'Signed');
  assert.doesNotMatch(signed, /Verified/);
  assert.equal(trustLabel({}), 'Unsigned');
  for (const label of [...labels, signed, trustLabel({})]) assert.doesNotMatch(label, /identity|author verified/i);
});

check('real floor metadata is distinct from absolute ellipsoidal height and unavailable height', () => {
  const record = records.find(record => record.mid === pairs[0][1]);
  const withFloor = mapRecordToAtom({ ...record, atom: { ...record.atom,
    x: JSON.stringify({ text: 'Floor fixture', meta: { floor: 0 } }),
  } });
  assert.match(heightLabel(withFloor), /Floor 0\b/);
  const height = heightLabel(mapRecordToAtom(record));
  assert.match(height, /23 m absolute WGS84 ellipsoidal height/);
  assert.doesNotMatch(height, /floor|above ground/i);
  assert.equal(heightLabel({}), 'Height unavailable');
});

check('Visible cards and shared count retain distant real roots; Activity includes replies', () => {
  const originalOrder = atoms.slice();
  const visible = atomsForTextTab(atoms, 'visible');
  assert.equal(visibleRootCount(atoms), 13);
  assert.equal(visibleRootCount(atoms), visible.length);
  assert.deepEqual(visible, atoms.filter(isRootAtom));
  // A street-scale Copenhagen viewport excludes the real South Pacific record.
  const inViewport = atom => atom.lat >= 55 && atom.lat <= 56 && atom.lon >= 12 && atom.lon <= 13;
  const distant = atoms.find(atom => atom.h === '0n5bvnczym_1');
  assert.ok(distant);
  assert.ok(distant.lat < -50 && distant.lon < -170);
  assert.equal(inViewport(distant), false);
  assert.ok(visible.includes(distant));
  assert.equal(visibleRootCount(atoms.filter(atom => atom !== distant)), visible.length - 1);
  const activity = atomsForTextTab(atoms, 'activity');
  assert.equal(activity.length, 15);
  assert.deepEqual(new Set(activity), new Set(atoms));
  assert.ok(activity.every((atom, index) => index === 0 || activity[index - 1].t >= atom.t));
  assert.deepEqual(atomsForTextTab(atoms, 'visible'), visible, 'switching back restores roots');
  assert.deepEqual(atoms, originalOrder, 'selection must not mutate its input');
  assert.equal(visibleRootCount([]), 0);
});

check('both real same-address replies group under one board, never as Visible cards', () => {
  for (const [replyId, parentId] of pairs) {
    const root = atoms.find(atom => atom.atom_id === parentId);
    const reply = atoms.find(atom => atom.atom_id === replyId);
    assert.equal(root.h, reply.h);
    if (parentId === pairs[0][1]) assert.equal(root.h, 'u3butz7k9q_23');
    assert.deepEqual(boardReplies(root, atoms), [reply]);
    assert.deepEqual(atomsForTextTab([root, reply]), [root]);
    assert.equal(visibleRootCount([root, reply]), 1);
    assert.ok(!atomsForTextTab(atoms).includes(reply));
    assert.ok(atomsForTextTab(atoms, 'activity').includes(reply));
  }
});

check('loading and recoverable error states never claim empty content', () => {
  const loading = readStateHtml({ loading: true });
  assert.match(loading, /role="status"/);
  assert.match(loading, /Loading published text/);
  const error = readStateHtml({ error: true });
  assert.match(error, /role="alert"/);
  assert.match(error, /Could not load/);
  assert.match(error, /try again/i);
  assert.match(error, /data-action="retry-read"/);
  for (const html of [loading, error]) assert.doesNotMatch(html, /nothing here|no public boards|no activity|empty/i);
  assert.equal(readStateHtml(), '');
  assert.equal(readStateHtml({ loading: false, error: false }), '');
});

check('existing explicit QA markers preserve the two genuine public posts', () => {
  assert.equal(atoms.filter(isQaRecord).length, 13);
  const genuine = atoms.filter(atom => !isQaRecord(atom));
  assert.equal(genuine.length, 2);
  assert.ok(genuine.some(atom => atom.x.startsWith('Welcome to Null Island')));
  assert.ok(genuine.some(atom => atom.x === 'Hello from a new AI'));
});

console.log(`${passed}/${passed} M8 UX checks passed (15 real records, 13 roots, 2 replies; QA 13 / public 2).`);
