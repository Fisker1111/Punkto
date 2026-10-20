"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const {
  b,
  ROOT,
  BIRTH,
  ROOTS,
  IAT,
  op,
  key,
  grant,
  event,
} = require("./helpers");
const copy = structuredClone;
function put(log, claims, s, iat = IAT + 1) {
  return b.append(log, "claim.set", { claims }, [s], { iat });
}
test("human actor from clean words authorizes operational key and sets human claim", () => {
  const words = b.entropyToWords(Buffer.alloc(32));
  const birth = b.buildBirth(b.deriveRootKeys(b.wordsToEntropy(words)));
  assert.deepEqual(birth, BIRTH);
  const log = b.newLog(birth),
    s = op();
  grant(log, s);
  put(log, { "actor.kind": "human" }, s);
  const state = b.deriveState(log);
  assert.equal(state.status, "OK");
  assert.equal(state.claims["actor.kind"], "human");
  assert.equal(state.seq, 2);
});
test("AI continuity, signed assertion, metadata changes, revocation, succession and historical evidence", () => {
  const log = b.newLog(BIRTH),
    s = op(2),
    next = op(3),
    identity = b.identityIdOf(BIRTH);
  grant(log, s);
  const claims = {
    "actor.kind": "ai",
    "model.family": "reference",
    "model.version": "1",
    runtime: "machine-a",
    operator: "operator-a",
  };
  const past = put(log, claims, s);
  const assertion = b.buildAttestation(
    {
      subject: identity,
      issuer: identity,
      claim: { assertion: "test-only AI assertion" },
      iat: IAT + 1,
      ref: b.hash(past),
    },
    [s],
  );
  assert.equal(b.verifyAttestation(assertion, log).ok, true);
  for (const update of [
    { "model.version": "2" },
    { runtime: "machine-b" },
    { operator: "operator-b" },
  ]) {
    put(log, update, s, IAT + 2);
    assert.equal(b.identityIdOf(log.birth), identity);
  }
  b.append(
    log,
    "revoke",
    { kid: b.kidOf(s.alg, s.pk), reason: "replace" },
    ROOTS,
    { iat: IAT + 3 },
  );
  assert.throws(() => put(log, { bad: true }, s, IAT + 4));
  b.append(
    log,
    "succeed",
    {
      from: [b.kidOf(s.alg, s.pk)],
      to: [{ ...key(next), scopes: ["sign", "claim"], not_after: null }],
      reason: "continuity",
    },
    ROOTS,
    { iat: IAT + 4 },
  );
  put(log, { "model.version": "3" }, next, IAT + 5);
  assert.equal(b.deriveState(log).status, "OK");
  assert.equal(b.identityIdOf(log.birth), identity);
  assert.equal(
    b.deriveState(log, { untilSeq: 2 }).keys[b.kidOf(s.alg, s.pk)].alg,
    b.ML,
  );
  assert.equal(b.verifyAttestation(assertion, log).ok, true);
  assert.equal(
    b.verify(
      s.alg,
      s.pk,
      b.encode(b.unsigned(past)),
      Buffer.from(past.sigs[0].sig, "base64url"),
    ),
    true,
  );
});
test("scoped authorization, expiry, claim deletion and no self-widening", () => {
  const log = b.newLog(BIRTH),
    s = op(4),
    other = op(5);
  grant(log, s, ["authority"], ROOTS, IAT, IAT + 10);
  assert.throws(() => put(log, { bad: 1 }, s));
  assert.throws(() => grant(log, s, ["authority", "claim"], [s], IAT + 1));
  assert.throws(() =>
    b.append(
      log,
      "succeed",
      {
        from: [b.kidOf(s.alg, s.pk)],
        to: [
          { ...key(s), scopes: ["authority", "claim"], not_after: IAT + 10 },
        ],
        reason: "escalate",
      },
      [s],
      { iat: IAT + 1 },
    ),
  );
  grant(log, other, ["claim"], [s], IAT + 2);
  put(log, { keep: 1, remove: 2 }, other, IAT + 3);
  b.append(log, "claim.del", { names: ["remove"] }, [other], { iat: IAT + 4 });
  assert.deepEqual(b.deriveState(log).claims, { keep: 1 });
  assert.throws(() => grant(log, op(6), ["sign"], [s], IAT + 11));
  b.append(
    log,
    "succeed",
    {
      from: [b.kidOf(s.alg, s.pk)],
      to: [{ ...key(s), scopes: ["authority"], not_after: IAT + 9 }],
      reason: "narrow",
    },
    [s],
    { iat: IAT + 5 },
  );
  assert.equal(b.deriveState(log).status, "OK");
});
test("root rotation uses prior dual policy, preserves ID and rejects old roots", () => {
  const log = b.newLog(BIRTH),
    rotated = b.deriveRootKeys(Buffer.alloc(32, 255)),
    root = b.buildBirth(rotated).root;
  b.append(log, "root.rotate", { root, reason: "rotate" }, ROOTS, { iat: IAT });
  assert.equal(b.identityIdOf(log.birth), b.identityIdOf(BIRTH));
  assert.throws(() => grant(log, op(7), ["sign"], ROOTS, IAT + 1));
  grant(log, op(7), ["sign"], b.rootSigners(rotated), IAT + 1);
  assert.equal(b.deriveState(log).status, "OK");
});
test("adversarial chain detects tampering, replay, forks, quorum and unknown fields", () => {
  const log = b.newLog(BIRTH),
    s = op(8);
  grant(log, s);
  const first = copy(log.events[0]);
  for (const mutate of [
    (e) => e.body.scopes.push("bad"),
    (e) => (e.prev = "A".repeat(43)),
    (e) => (e.seq = 2),
    (e) => (e.extra = true),
    (e) => (e.op = "unknown"),
    (e) => e.sigs.pop(),
    (e) => e.sigs.push(copy(e.sigs[0])),
  ]) {
    const e = copy(first);
    mutate(e);
    assert.equal(b.deriveState({ ...log, events: [e] }).status, "BROKEN");
  }
  const altered = copy(first);
  altered.body.scopes = ["sign"];
  assert.equal(b.deriveState({ ...log, events: [altered] }).status, "BROKEN");
  assert.equal(
    b.deriveState({ ...log, events: [first, first] }).status,
    "BROKEN",
  );
  const a = event(log, "claim.set", { claims: { a: 1 } }, [s]),
    c = event(log, "claim.set", { claims: { a: 2 } }, [s]);
  for (const events of [
    [first, a, c],
    [c, first, a],
  ]) {
    const state = b.deriveState({ ...log, events });
    assert.equal(state.status, "CONFLICTED");
    assert.equal(state.seq, 1);
    assert.equal(state.fork.hashes.length, 2);
  }
  const broken = copy(a);
  broken.prev = Buffer.alloc(32).toString("base64url");
  assert.equal(
    b.deriveState({ ...log, events: [first, broken, c] }).status,
    "BROKEN",
  );
  assert.throws(() => grant(log, op(9), ["sign"], [ROOTS[0]]));
  assert.throws(() => put(log, { bad: 1 }, op(10)));
  const invalid = event(log, "claim.set", { claims: { a: 3 } }, [op(11)]);
  assert.equal(
    b.deriveState({ ...log, events: [first, a, invalid] }).status,
    "BROKEN",
  );
  assert.throws(() => event(log, "unknown", {}, [s]));
  assert.throws(() => event(log, "claim.set", { claims: {}, extra: 1 }, [s]));
  assert.equal(b.deriveState(log, { untilSeq: 3 }).status, "BROKEN");
  assert.equal(b.deriveState(log).partial, true);
});

test("strict operation schemas reject unknown nested fields and wrong types", () => {
  const base = {
    type: "brth.event",
    v: 1,
    id: b.identityIdOf(BIRTH),
    seq: 1,
    prev: null,
    iat: IAT,
    sigs: [
      {
        alg: b.ML,
        kid: b.kidOf(ROOTS[0].alg, ROOTS[0].pk),
        sig: Buffer.alloc(4627).toString("base64url"),
      },
    ],
  };
  const s = op(23),
    kid = b.kidOf(s.alg, s.pk);
  const bodies = {
    authorize: { key: key(s), scopes: ["sign"], not_after: null },
    revoke: { kid, reason: "test" },
    succeed: {
      from: [kid],
      to: [{ ...key(s), scopes: ["sign"], not_after: null }],
      reason: "test",
    },
    "root.rotate": { root: BIRTH.root, reason: "test" },
    "claim.set": { claims: { a: 1 } },
    "claim.del": { names: ["a"] },
  };
  for (const [op, body] of Object.entries(bodies)) {
    assert.equal(b.verifyEvent({ ...base, op, body }).ok, true);
    assert.equal(
      b.verifyEvent({ ...base, op, body: { ...body, extra: 1 } }).ok,
      false,
    );
    assert.equal(b.verifyEvent({ ...base, op, body: null }).ok, false);
  }
  for (const body of [
    { ...bodies.authorize, key: { ...key(s), extra: true } },
    { ...bodies.authorize, scopes: "sign" },
    { ...bodies.authorize, not_after: "1" },
    { ...bodies.authorize, key: { alg: "ml-dsa-87", pk: key(s).pk } },
  ])
    assert.equal(b.verifyEvent({ ...base, op: "authorize", body }).ok, false);
  assert.equal(
    b.verifyEvent({ ...base, op: "claim.set", body: { claims: { a: 1.2 } } })
      .ok,
    false,
  );
});

test("operational SLH is a co-signature and cannot replace required ML-DSA", () => {
  const log = b.newLog(BIRTH),
    ml = op(24),
    root = b.deriveRootKeys(Buffer.alloc(32, 255));
  const slh = b.rootSigners(root)[1];
  grant(log, ml, ["sign"]);
  grant(log, slh, ["sign"]);
  const input = {
    subject: b.identityIdOf(BIRTH),
    issuer: b.identityIdOf(BIRTH),
    claim: { test: true },
    iat: IAT + 1,
    ref: null,
  };
  assert.equal(
    b.verifyAttestation(b.buildAttestation(input, [slh]), log).ok,
    false,
  );
  assert.equal(
    b.verifyAttestation(b.buildAttestation(input, [ml, slh]), log).ok,
    true,
  );
});
