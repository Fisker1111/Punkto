import { webcrypto } from 'node:crypto';
import { constants } from 'node:fs';
import { open, lstat, realpath } from 'node:fs/promises';
import path from 'node:path';

globalThis.crypto ??= webcrypto;

function httpURL(value, origin) {
  let url;
  try { url = new URL(value, origin); } catch { throw new Error('URL must be HTTP(S) without credentials'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error('URL must be HTTP(S) without credentials');
  }
  return url.href;
}

function argumentsFor(args) {
  const [action, ...rest] = args;
  if (!['read', 'reply', 'post'].includes(action)) throw new Error('command must be read, reply or post');
  const allowed = new Set(['origin', ...(action === 'read' ? ['limit'] : ['key-file']),
    ...(action === 'post' ? ['h', 'lat', 'lon', 'height'] : [])]);
  const options = {}, positional = [];
  for (let i = 0; i < rest.length; i++) {
    if (!rest[i].startsWith('--')) { positional.push(rest[i]); continue; }
    const name = rest[i].slice(2);
    if (!allowed.has(name)) throw new Error('unknown flag for ' + action);
    if (Object.hasOwn(options, name)) throw new Error('repeated flag for ' + action);
    if (rest[i + 1] === undefined || rest[i + 1].startsWith('--')) throw new Error('missing flag value for ' + action);
    options[name] = rest[++i];
  }
  if (positional.length !== { read: 0, reply: 2, post: 1 }[action]) {
    throw new Error('arguments: read; reply <MID> "text"; post "text" with an explicit address');
  }
  if (options.limit !== undefined && (!/^\d+$/.test(options.limit) || !Number.isSafeInteger(Number(options.limit)))) {
    throw new Error('read --limit must be a non-negative integer');
  }
  return { action, options, positional };
}

// Same dependency rewriting as the proven loader; no network imports or eval.
async function loadModules(origin, request) {
  const urls = {}, modules = {};
  const dataURL = source => 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
  const source = async name => {
    const response = await request(new URL(name, origin).href);
    if (!response.ok) throw new Error();
    return response.text();
  };
  try {
    const nacl = await source('/nacl.min.js');
    globalThis.nacl = (await import(dataURL(`globalThis.self = globalThis;\n${nacl}\nexport default globalThis.nacl;\n`))).default;
    for (const name of ['spatial.js', 'carrier.js', 'reader.js', 'submit.js']) {
      let code = await source('/punkti/' + name);
      for (const [dependency, url] of Object.entries(urls)) {
        code = code.split(`'./${dependency}'`).join(`'${url}'`);
      }
      urls[name] = dataURL(code);
      modules[name] = await import(urls[name]);
    }
    return modules;
  } catch { throw new Error('module loading failed: could not load frozen modules from the page origin'); }
}

async function localIdentity(filename) {
  if (filename === undefined) return globalThis.nacl.sign.keyPair();
  // Inspect metadata only: never read repository files or .git indirection files.
  let file;
  try {
    const absolute = path.resolve(filename);
    file = path.join(await realpath(path.dirname(absolute)), path.basename(absolute));
    for (let dir = path.dirname(file); ; dir = path.dirname(dir)) {
      const exists = async name => { try { await lstat(path.join(dir, name)); return true; } catch (e) { if (e.code === 'ENOENT') return false; throw e; } };
      if (await exists('.git') || (await exists('HEAD') && await exists('objects') && await exists('refs'))) {
        throw new Error('repository');
      }
      if (path.dirname(dir) === dir) break;
    }
  } catch (error) {
    if (error.message === 'repository') throw new Error('key custody: key file must be outside any git repository');
    throw new Error('key custody: cannot inspect key file directory');
  }
  let handle;
  try {
    try {
      handle = await open(file, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY, 0o600);
      await handle.chmod(0o600);
      const seed = globalThis.crypto.getRandomValues(new Uint8Array(32));
      await handle.writeFile(Buffer.from(seed).toString('hex'));
      return globalThis.nacl.sign.keyPair.fromSeed(seed);
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const metadata = await lstat(file);
      if (!metadata.isFile() || metadata.nlink !== 1) throw new Error();
      handle = await open(file, constants.O_RDONLY | constants.O_NOFOLLOW);
      if (!(await handle.stat()).isFile()) throw new Error();
      await handle.chmod(0o600);
      const seed = await handle.readFile('utf8');
      if (!/^[0-9a-f]{64}$/.test(seed)) throw new Error();
      return globalThis.nacl.sign.keyPair.fromSeed(new Uint8Array(Buffer.from(seed, 'hex')));
    }
  } catch { throw new Error('key custody: cannot load or create a private 32-byte lowercase hex seed'); }
  finally { await handle?.close(); }
}

async function run(args) {
  const { action, options, positional } = argumentsFor(args);
  const origin = new URL(httpURL(options.origin ?? process.env.PUNKTO_ORIGIN ?? 'https://punkto.xyz')).origin;
  const request = (address, init = {}) => fetch(httpURL(address, origin), {
    ...init, redirect: 'error', signal: AbortSignal.timeout(10000),
  });
  let bootstrap;
  try {
    const response = await request(origin + '/nodes.json');
    if (!response.ok) throw new Error();
    bootstrap = await response.json();
  } catch { throw new Error('bootstrap failed: node unreachable or invalid nodes.json response'); }
  if (bootstrap?.v !== 'punkti/bootstrap/1' || !Array.isArray(bootstrap.nodes) || !bootstrap.nodes.length) {
    throw new Error('bootstrap failed: expected punkti/bootstrap/1 and a non-empty nodes array');
  }
  const nodes = bootstrap.nodes.map(node => {
    if (!node || typeof node.base !== 'string' || typeof node.publication !== 'string') throw new Error('bootstrap failed: node base and publication required');
    return { id: node.id, base: httpURL(node.base, origin), publication: httpURL(node.publication, origin),
      ...(node.submit ? { submit: httpURL(node.submit, origin) } : {}) };
  });
  const own = node => new URL(node.base).origin === origin;
  const readNode = nodes.find(own) ?? nodes[0];
  const writeNode = nodes.find(node => own(node) && node.submit) ?? nodes.find(node => node.submit);
  if (action !== 'read' && !writeNode) throw new Error('selected node does not accept writes (no submit entry)');
  const modules = await loadModules(origin, request);
  const { State, VERSION, b64, encodeRecord } = modules['carrier.js'];
  const { parse_h, encode_h } = modules['spatial.js'];
  const read = async node => {
    try {
      return await modules['reader.js'].createReader({ fetchImpl: request, maxRetries: 0 }).readPublication(node.publication);
    } catch (error) { throw new Error('publication read failed: ' + (error.reason ?? 'invalid publication')); }
  };
  if (action === 'read') {
    const publication = await read(readNode);
    return { ok: true, publication: { head: publication.head, seq: publication.seq },
      records: publication.valid_records.slice(0, options.limit === undefined ? Infinity : Number(options.limit)).map(({ mid, h, atom, state }) => {
        let text = atom.x;
        try { text = JSON.parse(atom.x).text ?? atom.x; } catch {}
        return { mid, h, text, state };
      }) };
  }
  let h, parent = null;
  if (action === 'reply') {
    const publication = await read(readNode);
    const record = [...publication.records, ...publication.quarantined].find(record => record.mid === positional[0]);
    if (!record) throw new Error('parent MID not found in the publication; discover it with read');
    if (record.state !== State.VALID) throw new Error(`parent record is not signature-verified (state=${record.state})`);
    h = record.h;
    parent = { mid: record.mid, h, verified: true };
  } else {
    const coords = ['lat', 'lon', 'height'];
    const hasCoords = coords.some(name => options[name] !== undefined);
    if (options.h !== undefined && hasCoords) throw new Error('post address: choose --h or coordinates, not both');
    if (options.h !== undefined) {
      try { parse_h(options.h); } catch { throw new Error('post address: invalid --h; use canonical <xy>_<z>'); }
      h = options.h;
    } else {
      if (!coords.every(name => options[name] !== undefined && options[name].trim() !== '')) {
        throw new Error('post address: explicit --h or --lat, --lon and --height required; never guess height');
      }
      try { h = encode_h(Number(options.lat), Number(options.lon), options.height); }
      catch { throw new Error('post address: invalid --lat, --lon or --height'); }
    }
  }
  const identity = await localIdentity(options['key-file']);
  const client = modules['submit.js'].createSubmitClient({ baseUrl: writeNode.base, identity,
    fetchImpl: (_url, init) => request(writeNode.submit, init) });
  const atom = { v: VERSION, t: Date.now(), h,
    x: JSON.stringify({ text: positional[action === 'reply' ? 1 : 0] }), alg: 'ed25519',
    refs: parent ? [{ target: parent.mid, rel: 'reply' }] : [], ext: '' };
  const encoded = await encodeRecord(atom, identity.secretKey);
  const result = await client.submit(atom);
  if (!result.ok) throw new Error('submit failed: ' + result.error);
  if (result.mid !== encoded.address || result.sha256 !== encoded.sha256 || result.state !== State.VALID) {
    throw new Error('submit failed: acknowledgement does not match the locally signed record');
  }
  const warnings = ['Ed25519 is not post-quantum secure.',
    'An ephemeral key is not a durable identity.',
    'A signature proves control of a key, not the truth of the text or the author\'s location.',
    'Acceptance is not publication or preservation; nothing is guaranteed to survive forever.'];
  if (result.duplicate) warnings.push('The node reported a duplicate record.');
  let publication = null, published;
  try {
    publication = await read(writeNode);
    published = [...publication.records, ...publication.quarantined].find(record => record.mid === result.mid);
  } catch (error) { warnings.push(error.message); }
  const visible = Boolean(published);
  const verified = visible && published.state === State.VALID && published.h === h && published.sha256 === result.sha256;
  if (!visible) warnings.push('Accepted, but not visible in a fresh publication read; publication may lag acceptance.');
  else if (!verified) warnings.push('Published bytes did not pass local verification for this submission.');
  return { ok: true, action, mid: result.mid, h, parent, submitted: true, submit_state: result.state,
    duplicate: result.duplicate, visible, verified, replicated: 'not-measured', public_key: b64(identity.publicKey),
    key: options['key-file'] === undefined ? 'ephemeral' : 'persistent', node: writeNode,
    publication: { head: publication?.head ?? null, seq: publication?.seq ?? null }, warnings };
}

try { console.log(JSON.stringify(await run(process.argv.slice(2)))); }
catch (error) { console.log(JSON.stringify({ ok: false, error: error.message })); process.exitCode = 1; }
