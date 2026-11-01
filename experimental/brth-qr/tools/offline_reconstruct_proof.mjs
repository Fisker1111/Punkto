import { fork, spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { mkdtempSync, readFileSync, writeFileSync, rmSync, mkdirSync } from 'node:fs';
import { dirname, resolve, delimiter } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { brth, capsule, uncapsule, sha256, require } from './capsule.mjs';
const bridge = require('../../brth-layer4/tools/pq-openssl');
const here = fileURLToPath(import.meta.url);
const root = resolve(dirname(here), '..');
const message = Buffer.from('BRTH QR R1 cross-process continuity');
const minimal = { PATH: [dirname(process.execPath), '/usr/local/bin', '/usr/bin', '/bin'].join(delimiter),
  LANG: 'C', LC_ALL: 'C', PYTHONDONTWRITEBYTECODE: '1' };
function publicEvidence(roots) {
  const birth = brth.buildBirth(roots);
  return { birth: brth.encode(birth).toString('base64'), identity_id: brth.identityIdOf(birth),
    ml_public_sha256: sha256(roots.ml.pk), slh_public_sha256: sha256(roots.slh.pk) };
}
function signatures(roots) {
  return brth.rootSigners(roots).map(s => ({ alg: s.alg,
    signature: brth.sign(s.alg, s.sk, message).toString('base64') }));
}
function verify(roots, sigs) {
  for (const [i, s] of brth.rootSigners(roots).entries()) {
    const sig = Buffer.from(sigs[i].signature, 'base64');
    assert.equal(sigs[i].alg, s.alg);
    assert.equal(bridge.verify(s.alg, s.pk, message, sig), true);
    assert.equal(brth.verify(s.alg, s.pk, message, sig), true);
    assert.equal(bridge.verify(s.alg, s.pk, Buffer.from('tampered'), sig), false);
  }
}
if (process.argv[2] === '--generate') {
  try {
    // Public, non-secret TEST vector: 32 zero bytes. Never use for production.
    const entropy = process.argv.includes('--random') ? randomBytes(32) : Buffer.alloc(32);
    const words = brth.entropyToWords(entropy);
    const roots = brth.deriveRootKeys(brth.wordsToEntropy(words));
    const bytes = capsule(entropy);
    // This file is public evidence only; reconstruction reads it after derivation.
    writeFileSync('before.json', JSON.stringify({ ...publicEvidence(roots),
      entropy_sha256: sha256(entropy), signatures: signatures(roots) }));
    process.send({ capsule: bytes.toString('base64') }, () => process.disconnect());
  } catch { process.exitCode = 1; process.disconnect(); }
} else if (process.argv[2] === '--reconstruct') {
  try {
    const bytes = readFileSync(0), entropy = uncapsule(bytes);
    const words = brth.entropyToWords(entropy);
    const fromWords = brth.wordsToEntropy(words);
    assert.deepEqual(fromWords, entropy);
    const roots = brth.deriveRootKeys(fromWords), actual = publicEvidence(roots);
    const direct = publicEvidence(brth.deriveRootKeys(entropy));
    assert.deepEqual(actual, direct);
    // Exercise the unchanged recovery API as well; no history lookup is needed for genesis.
    const recovery = brth.recoverFromWords(words, { head: null, iat: 1760000000 });
    assert.equal(recovery.identityId, actual.identity_id);
    assert.equal(brth.encode(recovery.birth).toString('base64'), actual.birth);
    const before = JSON.parse(readFileSync('before.json', 'utf8'));
    for (const key of Object.keys(actual)) assert.equal(actual[key], before[key]);
    assert.equal(sha256(entropy), before.entropy_sha256);
    verify(roots, before.signatures);
    const after = signatures(roots);
    verify(roots, after);
    const log = brth.newLog(recovery.birth);
    log.events.push(recovery.recoveryEvent);
    assert.equal(brth.deriveState(log).status, 'OK');
    writeFileSync('after.json', JSON.stringify({ identity_id: actual.identity_id,
      birth_bytes: Buffer.from(actual.birth, 'base64').length,
      birth_sha256: sha256(Buffer.from(actual.birth, 'base64')),
      ml_public_sha256: actual.ml_public_sha256, slh_public_sha256: actual.slh_public_sha256,
      entropy_sha256: sha256(entropy), capsule_sha256: sha256(bytes), capsule_bytes: bytes.length,
      signature_bytes: after.map(s => ({ algorithm: s.alg, bytes: Buffer.from(s.signature, 'base64').length })),
      verdicts: { words_entropy_capsule_equal: true, birth_byte_identical: true,
        identity_id_identical: true, public_key_hashes_identical: true,
        before_signatures_verify_both_families: true, after_signatures_verify_openssl_both_families: true,
        tampering_rejected_both_families: true, recovery_api_same_identity: true,
        recovery_event_authority_valid: true } }));
  } catch { process.stderr.write('Reconstruction failed; sensitive diagnostics suppressed\n'); process.exitCode = 1; }
} else {
  mkdirSync(resolve(root, '.work'), { recursive: true });
  const cwd = mkdtempSync(resolve(root, '.work/offline-'));
  try {
    const version = spawnSync('openssl', ['version'], { env: minimal, encoding: 'utf8' });
    assert.equal(version.status, 0);
    assert.match(version.stdout, /^OpenSSL 3\.5\.5 /);
    const isolation = spawnSync('unshare', ['-n', 'true'], { env: minimal, encoding: 'utf8' });
    // Generation lives in a separate process which exits before reconstruction starts.
    // Its only secret output retained by this coordinator is the capsule.
    const bytes = await new Promise((accept, reject) => {
      let retained;
      const child = fork(here, ['--generate', ...(process.argv.includes('--random') ? ['--random'] : [])], { cwd, env: minimal, stdio: ['ignore','ignore','ignore','ipc'] });
      child.on('message', msg => { retained = Buffer.from(msg.capsule, 'base64'); });
      child.on('error', reject);
      child.on('exit', code => code === 0 && retained ? accept(retained) : reject(Error('generation failed')));
    });
    const isolated = isolation.status === 0;
    const program = isolated ? 'unshare' : process.execPath;
    const args = isolated ? ['-n', process.execPath, here, '--reconstruct'] : [here, '--reconstruct'];
    const child = spawnSync(program, args, { cwd, env: minimal, input: bytes, encoding: 'utf8', timeout: 240000 });
    bytes.fill(0);
    assert.equal(child.status, 0, 'fresh reconstruction failed (private diagnostics suppressed)');
    const result = JSON.parse(readFileSync(resolve(cwd, 'after.json'), 'utf8'));
    result.openssl = version.stdout.trim();
    result.isolation = { attempted_command: 'unshare -n true', exit_code: isolation.status,
      stderr: isolation.stderr?.trim() || '', kernel_network_namespace: isolated,
      actual: 'fresh generator exits; fresh reconstruction process; temporary cwd; minimal environment; no DNS or network calls attempted',
      limitation: isolated ? 'no network namespace interfaces configured' : 'network access was not blocked by the kernel; absence of attempted calls is code inspection, not a packet trace' };
    result.verdicts.generator_exited_before_reconstruction = true;
    result.verdicts.fresh_process_and_directory = true;
    mkdirSync(resolve(root, 'out'), { recursive: true });
    writeFileSync(resolve(root, 'out/offline_proof.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result, null, 2));
  } finally { rmSync(cwd, { recursive: true, force: true }); }
}
