"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const { b, BIRTH, op, grant, IAT } = require("./helpers");
function python(input) {
  const r = spawnSync("python3", [path.join(__dirname, "layering_runner.py")], {
    input: JSON.stringify(input),
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    maxBuffer: 2 ** 20,
  });
  assert.equal(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}
function roundTrip(payload) {
  const privateKey = crypto.createPrivateKey({
      key: Buffer.concat([
        Buffer.from("302e020100300506032b657004220420", "hex"),
        Buffer.alloc(32, 42),
      ]),
      format: "der",
      type: "pkcs8",
    }),
    publicKey = crypto
      .createPublicKey(privateKey)
      .export({ format: "der", type: "spki" })
      .subarray(-32);
  const atom = {
    v: "punkti/0.6",
    t: 1760000000000,
    h: "",
    x: "brth/1:" + b.encode(payload).toString(),
    alg: "ed25519",
    pk: publicKey.toString("base64"),
    refs: [],
    ext: "",
    sig: Buffer.alloc(64).toString("base64"),
  };
  const body = Buffer.from(python({ mode: "canonical", atom }).body, "base64");
  atom.sig = crypto
    .sign(
      null,
      Buffer.concat([Buffer.from("PUNKTI-L3-SIGN\0"), body]),
      privateKey,
    )
    .toString("base64");
  const result = python({ mode: "roundtrip", atom });
  assert.equal(result.x, atom.x);
  assert.equal(result.body, body.toString("base64"));
  assert.equal(result.state, "VALID");
  assert.equal(result.opaque, true);
  assert.equal(result.stored, 1);
  const lp = (x) => {
    const size = Buffer.alloc(4);
    size.writeUInt32BE(x.length);
    return Buffer.concat([size, x]);
  };
  assert.deepEqual(
    Buffer.from(result.record, "base64"),
    Buffer.concat([lp(body), lp(Buffer.from(atom.sig, "base64"))]),
  );
}
test("Punkti Layer-3 opaque BRTH bytes survive real carrier and mesh store/transport", () =>
  roundTrip(BIRTH));
test("AI signed assertion is published as an opaque carrier atom", () => {
  const log = b.newLog(BIRTH),
    signer = op(22);
  grant(log, signer);
  b.append(
    log,
    "claim.set",
    {
      claims: {
        "actor.kind": "ai",
        "model.family": "reference",
        "model.version": "1",
        runtime: "machine-a",
        operator: "operator-a",
      },
    },
    [signer],
    { iat: IAT + 1 },
  );
  const identity = b.identityIdOf(BIRTH);
  const assertion = b.buildAttestation(
    {
      subject: identity,
      issuer: identity,
      claim: { assertion: "test-only AI assertion" },
      iat: IAT + 2,
      ref: null,
    },
    [signer],
  );
  assert.equal(b.verifyAttestation(assertion, log).ok, true);
  roundTrip(assertion);
});
