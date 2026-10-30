import assert from 'node:assert/strict';
import http from 'node:http';
import { mkdtempSync, writeFileSync, rmSync, copyFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import './punkti/cli.mjs';
import { encodeRecord } from './punkti/carrier.js';
import { createReader } from './punkti/reader.js';
import { createSubmitClient } from './punkti/submit.js';
import { parse_h, decode_xy, encode_h } from './punkti/spatial.js';

export const ROOT = fileURLToPath(new URL('../', import.meta.url));
export async function cli(args, filename = path.join(ROOT, 'pwa/punkti/cli.mjs')) {
  const child = spawn(process.execPath, [filename, ...args], { cwd: ROOT });
  let stdout = '', stderr = '';
  child.stdout.on('data', chunk => { stdout += chunk; });
  child.stderr.on('data', chunk => { stderr += chunk; });
  const timer = setTimeout(() => child.kill('SIGKILL'), 20000);
  try {
    const [code] = await once(child, 'exit');
    assert.ok(stdout.trim(), stderr);
    return { code, body: JSON.parse(stdout), stderr };
  } finally { clearTimeout(timer); }
}
export async function localNode() {
  const directory = mkdtempSync(path.join(tmpdir(), 'punkti-ai-'));
  const server = http.createServer();
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  const base = `http://127.0.0.1:${port}`;
  const configPath = path.join(directory, 'config.json');
  writeFileSync(configPath, JSON.stringify({
    web: { root: path.join(ROOT, 'pwa') },
    network: { listen_host: '127.0.0.1', listen_port: port, peers: [], sync_interval_seconds: 3600 },
    storage: { data_path: path.join(directory, 'data') },
    bootstrap: { nodes: [{ id: 'local', base, publication: `${base}/publication`, submit: `${base}/submit` }] },
  }));
  let child;
  async function stop() {
    if (child && child.exitCode === null && child.signalCode === null) {
      const exited = once(child, 'exit'); child.kill('SIGTERM');
      const timer = setTimeout(() => child.kill('SIGKILL'), 5000);
      try { await exited; } finally { clearTimeout(timer); }
    }
  }
  async function start() {
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('PUNKTO_')));
    child = spawn('python3', ['-m', 'punkti_node', '--config', configPath], { cwd: ROOT, env });
    let logs = '';
    child.stdout.on('data', chunk => { logs += chunk; });
    child.stderr.on('data', chunk => { logs += chunk; });
    for (let attempt = 0; attempt < 100; attempt++) {
      if (child.exitCode !== null) throw new Error(logs);
      try { if ((await fetch(`${base}/health`, { signal: AbortSignal.timeout(500) })).ok) return; } catch {}
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error(`node startup failed: ${logs}`);
  }
  try { await start(); } catch (error) { await stop(); rmSync(directory, { recursive: true, force: true }); throw error; }
  return { base, directory, start, stop, async close() { await stop(); rmSync(directory, { recursive: true, force: true }); } };
}
async function main() {
  const node = await localNode();
  try {
    const nodesUrl = `${node.base}/nodes.json`;
    const bootstrap = await (await fetch(nodesUrl)).json();
    assert.equal(bootstrap.v, 'punkti/bootstrap/1');
    assert.equal(bootstrap.nodes.length, 1);
    const selected = bootstrap.nodes[0];
    assert.equal(selected.base, node.base);
    const identity = globalThis.nacl.sign.keyPair();
    assert.equal(identity.secretKey.length, 64);
    const atom = { t: Date.now(), h: 'u3butz7k9q7v_0', x: JSON.stringify({ text: 'E1 seed' }) };
    const signed = await encodeRecord(atom, identity.secretKey);
    assert.match(signed.address, /^punkti\/0\.6:[0-9a-f]{64}$/);
    const submitted = await createSubmitClient({ baseUrl: node.base, identity }).submit(atom);
    assert.equal(submitted.ok, true);
    const reader = createReader({ maxRetries: 0 });
    const first = await reader.readPublication(selected.publication);
    assert.equal(first.valid_count, 1);
    assert.equal(first.records[0].mid, submitted.mid);
    assert.equal(first.records[0].state, 'VALID');
    const { xy, z } = parse_h(atom.h);
    const { lat, lon } = decode_xy(xy);
    assert.equal(encode_h(lat, lon, z, xy.length), atom.h);
    assert.equal(encode_h(55.675398, 12.561895, 0, 12), atom.h);
    const written = await cli(['write', '--nodes', nodesUrl, '--text', 'E1 coordinates', '--lat', '55.675398', '--lon', '12.561895', '--height', '0']);
    assert.equal(written.code, 0, written.body.error);
    assert.equal(written.body.duplicate, false);
    const readback = await cli(['read', '--nodes', nodesUrl]);
    assert.equal(readback.code, 0);
    const record = readback.body.records.find(record => record.mid === written.body.mid);
    assert.equal(record.state, 'VALID');
    assert.equal(record.text, 'E1 coordinates');
    assert.equal(record.h, encode_h(55.675398, 12.561895, 0));
    const reply = await cli(['reply', '--nodes', nodesUrl, '--ref', written.body.mid, '--text', 'E1 reply', '--h', record.h]);
    assert.equal(reply.code, 0, reply.body.error);
    const replied = await reader.readPublication(selected.publication);
    assert.deepEqual(replied.records.find(record => record.mid === reply.body.mid).atom.refs, [{ target: written.body.mid, rel: 'reply' }]);
    assert.notEqual(replied.records.find(record => record.mid === reply.body.mid).atom.pk, first.records[0].atom.pk);
    const flat = path.join(node.directory, 'cli.mjs');
    for (const filename of ['cli.mjs', 'carrier.js', 'reader.js', 'spatial.js', 'submit.js']) copyFileSync(path.join(ROOT, 'pwa/punkti', filename), path.join(node.directory, filename));
    copyFileSync(path.join(ROOT, 'pwa/nacl.min.js'), path.join(node.directory, 'nacl.min.js'));
    const flatRead = await cli(['read', '--nodes', nodesUrl, '--xy', 'u3butz', '--z-min', '0', '--z-max', '1', '--limit', '1'], flat);
    assert.equal(flatRead.code, 0, flatRead.body.error);
    assert.equal(flatRead.body.records.length, 1);
    const flatWrite = await cli(['write', '--nodes', nodesUrl, '--text', 'E1 flat write', '--h', atom.h], flat);
    assert.equal(flatWrite.code, 0, flatWrite.body.error);
    await node.stop(); await node.start();
    const persisted = await createReader().readPublication(selected.publication);
    assert.equal(persisted.valid_count, 4);
    for (const mid of [submitted.mid, written.body.mid, reply.body.mid, flatWrite.body.mid]) assert.ok(persisted.valid_records.some(record => record.mid === mid));
    console.log('E1: PASS — all eleven cold-start steps, flat helper, scoped read, restart persistence');
  } finally { await node.close(); }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
