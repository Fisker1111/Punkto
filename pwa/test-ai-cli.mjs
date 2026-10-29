import assert from 'node:assert/strict';
import { localNode, cli } from './test-ai-coldstart.mjs';
import { run } from './punkti/cli.mjs';
import { encode_h } from './punkti/spatial.js';
import { createReader } from './punkti/reader.js';

const node = await localNode();
try {
  const nodes = `${node.base}/nodes.json`;
  const publication = `${node.base}/publication`;
  const expectedH = encode_h(-33.9, -0.0015, -45);
  const mids = [];
  for (const equals of [false, true]) {
    const options = { nodes, text: '-CLI=value=preserved', lat: '-33.9', lon: '-0.0015', height: '-45', submit: `${node.base}/submit` };
    const args = Object.entries(options).flatMap(([key, value]) => equals ? [`--${key}=${value}`] : [`--${key}`, value]);
    const result = await cli(['write', ...args]);
    assert.equal(result.code, 0, result.body.error);
    mids.push(result.body.mid);
  }
  const exactH = encode_h(55.675398, 12.561895, 0);
  const anchored = await cli(['write', `--nodes=${nodes}`, '--text=exact h', `--h=${exactH}`]);
  assert.equal(anchored.code, 0, anchored.body.error);
  const reply = await cli(['reply', `--nodes=${nodes}`, `--ref=${anchored.body.mid}`, '--text=reply', `--h=${exactH}`]);
  assert.equal(reply.code, 0, reply.body.error);
  assert.equal(reply.body.ref, anchored.body.mid);
  const records = (await createReader().readPublication(publication)).records;
  for (const mid of mids) {
    const record = records.find(record => record.mid === mid);
    assert.equal(record.state, 'VALID');
    assert.equal(record.h, expectedH);
    assert.equal(JSON.parse(record.atom.x).text, '-CLI=value=preserved');
  }
  assert.equal(records.find(record => record.mid === anchored.body.mid).h, exactH);
  assert.deepEqual(records.find(record => record.mid === reply.body.mid).atom.refs, [{ target: anchored.body.mid, rel: 'reply' }]);
  const read = await cli(['read', `--nodes=${nodes}`, `--publication=${publication}`, `--xy=${expectedH.split('_')[0]}`, '--z-min=-46', '--z-max=-44', '--limit=1']);
  assert.equal(read.code, 0, read.body.error);
  assert.equal(read.body.records.length, 1);
  assert.ok(mids.includes(read.body.records[0].mid));
  assert.equal(read.body.records[0].h, expectedH);

  // Prove endpoint overrides are used, rather than merely accepted as tokens.
  const seen = [];
  const fetchOverride = (address, init) => {
    seen.push(address);
    return fetch(address.replace('/custom-publication', '/publication').replace('/custom-submit', '/submit'), init);
  };
  await run(['read', `--nodes=${nodes}`, `--publication=${node.base}/custom-publication`], fetchOverride);
  await run(['write', `--nodes=${nodes}`, `--submit=${node.base}/custom-submit`, '--text=--literal', `--h=${exactH}`], fetchOverride);
  assert.ok(seen.includes(`${node.base}/custom-publication/root.json`));
  assert.ok(seen.includes(`${node.base}/custom-submit`));

  for (const [flags, message] of [
    [['--unknown=value'], /unknown option/],
    [['--unknown', 'value'], /unknown option/],
    [['--text'], /missing value/],
    [['--text', '--lat=1'], /missing value/],
    [['--text=one', '--text', 'two'], /repeated option/],
    [['--text', 'one', '--text=two'], /repeated option/],
    [['--text=one', '--text=two'], /repeated option/],
    [['--text', 'one', '--text', 'two'], /repeated option/],
    [['--text=test', '--lat=-33.9', '--lon=-0.0015'], /--lat, --lon and --height are required together; never invent ellipsoidal height/],
    [['--text=test', `--h=${exactH}`, '--lat=-33.9', '--lon=-0.0015', '--height=-45'], /choose --h or coordinates/],
  ]) {
    const result = await cli(['write', `--nodes=${nodes}`, ...flags]);
    assert.notEqual(result.code, 0);
    assert.deepEqual(Object.keys(result.body), ['error']);
    assert.match(result.body.error, message);
  }
  // Only valid commands/options can reach the required-spatial-address gate.
  // 'post' is not a CLI command; 'write --ref' is an unknown option.
  for (const [command, extra] of [
    ['write', []],
    ['reply', [`--ref=${anchored.body.mid}`]],
  ]) {
    const result = await cli([command, `--nodes=${nodes}`, '--text=missing h', ...extra]);
    assert.equal(result.code, 1);
    assert.match(result.body.error, /spatial address required: pass --h <xy>_<z> or --lat\/--lon\/--height/);
  }
  const badCommand = await cli(['post', `--nodes=${nodes}`, '--text=missing h']);
  assert.equal(badCommand.code, 1);
  assert.match(badCommand.body.error, /expected read, write or reply/);
  const badWriteOption = await cli(['write', `--nodes=${nodes}`, '--text=missing h', `--ref=${anchored.body.mid}`]);
  assert.equal(badWriteOption.code, 1);
  assert.match(badWriteOption.body.error, /unknown option --ref/);
  for (const h of ['', 'broken', 'u3bu_-0', 'U3bu_0']) {
    const result = await cli(['write', `--nodes=${nodes}`, '--text=invalid h', `--h=${h}`]);
    assert.equal(result.code, 1);
    assert.match(result.body.error, /invalid spatial address/);
  }
  // L3 carries opaque refs: equality is enforced by Punkto L4, not this helper.
  const elsewhere = await cli(['reply', `--nodes=${nodes}`, `--ref=${anchored.body.mid}`, '--text=opaque reference', '--h=ezs42_99']);
  assert.equal(elsewhere.code, 0, elsewhere.body.error);
  console.log('CLI: PASS — both option forms, all documented flags, negative coordinates/height, overrides, JSON failures and repeated-flag rejection');
} finally { await node.close(); }
