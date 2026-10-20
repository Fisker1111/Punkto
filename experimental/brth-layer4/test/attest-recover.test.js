"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { b, BIRTH, ROOT, ROOTS, IAT, op, grant } = require("./helpers");
test("attestations verify issuer authority and keep subject identity/state separate", () => {
  const issuer = b.newLog(BIRTH),
    s = op(12);
  grant(issuer, s, ["sign"]);
  const subject = b.newLog(
    b.buildBirth(b.deriveRootKeys(Buffer.alloc(32, 255))),
  );
  const before = b.encode(subject);
  const a = b.buildAttestation(
    {
      subject: b.identityIdOf(subject.birth),
      issuer: b.identityIdOf(BIRTH),
      claim: {
        "actor.kind": "human",
        "legal.name": "Test Person",
        scheme: "test",
      },
      iat: IAT + 1,
      ref: null,
    },
    [s],
  );
  assert.equal(b.verifyAttestation(a, issuer).ok, true);
  assert.equal(
    b.verifyAttestation({ ...a, claim: { "actor.kind": "ai" } }, issuer).ok,
    false,
  );
  assert.equal(b.verifyAttestation({ ...a, extra: 1 }, issuer).ok, false);
  const unauthorized = b.buildAttestation(
    {
      subject: a.subject,
      issuer: a.issuer,
      claim: a.claim,
      iat: a.iat,
      ref: null,
    },
    [op(13)],
  );
  assert.equal(b.verifyAttestation(unauthorized, issuer).ok, false);
  assert.equal(b.verifyAttestation(a, subject).ok, false);
  assert.equal(b.verifyAttestation(a, issuer, { atIat: IAT - 1 }).ok, false);
  assert.deepEqual(b.encode(subject), before);
  assert.deepEqual(b.deriveState(subject).claims, {});
  b.append(
    issuer,
    "revoke",
    { kid: b.kidOf(s.alg, s.pk), reason: "retire" },
    ROOTS,
    { iat: IAT + 2 },
  );
  assert.equal(b.verifyAttestation(a, issuer).ok, true);
  const later = b.buildAttestation(
    {
      subject: a.subject,
      issuer: a.issuer,
      claim: a.claim,
      iat: IAT + 3,
      ref: null,
    },
    [s],
  );
  assert.equal(b.verifyAttestation(later, issuer).ok, false);
});
test("paper recovery in fresh process reproduces Birth and roots and appends fresh authority", () => {
  const words = b.entropyToWords(Buffer.alloc(32));
  const log = b.newLog(BIRTH);
  grant(log, op(14));
  const script = `const b=require('./src');let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{const i=JSON.parse(s);const r=b.recoverFromWords(i.words,{head:i.head,iat:i.iat,operationalSeed:Buffer.alloc(32,15)});process.stdout.write(JSON.stringify({birth:r.birth,identityId:r.identityId,recoveryEvent:r.recoveryEvent,ml:r.rootKeys.ml.pk.toString('hex'),slh:r.rootKeys.slh.pk.toString('hex')}));});`;
  const result = spawnSync(process.execPath, ["-e", script], {
    cwd: path.join(__dirname, ".."),
    input: JSON.stringify({ words, head: log, iat: IAT + 1 }),
    encoding: "utf8",
    maxBuffer: 2 ** 20,
  });
  assert.equal(result.status, 0, result.stderr);
  const recovered = JSON.parse(result.stdout);
  assert.deepEqual(b.encode(recovered.birth), b.encode(BIRTH));
  assert.equal(recovered.identityId, b.identityIdOf(BIRTH));
  assert.equal(recovered.ml, ROOT.ml.pk.toString("hex"));
  assert.equal(recovered.slh, ROOT.slh.pk.toString("hex"));
  log.events.push(recovered.recoveryEvent);
  assert.equal(b.deriveState(log).status, "OK");
  assert.ok(b.deriveState(log).keys[b.kidOf(op(15).alg, op(15).pk)]);
  const published = Buffer.concat([
    b.encode(log),
    ...["root", "birth"].map((n) =>
      fs.readFileSync(path.join(__dirname, "../vectors", n + ".json")),
    ),
  ]);
  assert.equal(published.includes(Buffer.alloc(32)), false);
  assert.equal(published.includes(words), false);
  assert.equal(
    published.includes(Buffer.alloc(32).toString("base64url")),
    false,
  );
  assert.equal(published.includes(Buffer.alloc(32).toString("hex")), false);
  const rotated = b.newLog(BIRTH);
  b.append(
    rotated,
    "root.rotate",
    {
      root: b.buildBirth(b.deriveRootKeys(Buffer.alloc(32, 255))).root,
      reason: "rotate",
    },
    ROOTS,
    { iat: IAT },
  );
  assert.throws(() =>
    b.recoverFromWords(words, {
      head: rotated,
      iat: IAT + 1,
      operationalSeed: Buffer.alloc(32, 16),
    }),
  );
});
