"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const { b, ROOT, ROOTS } = require("./helpers");
const bridge = require("../tools/pq-openssl");
const { slh_dsa_shake_256s } = require("@noble/post-quantum/slh-dsa.js");
test(
  "independent OpenSSL ML-DSA and SLH-DSA interoperability both directions and exact sizes",
  { timeout: 180000 },
  (t) => {
    if (!bridge.capable()) {
      t.skip(
        "OpenSSL binary lacks SLH-DSA-SHAKE-256s; noble fallback remains available",
      );
      return;
    }
    const msg = Buffer.from("BRTH/1 independent implementation test");
    for (const s of ROOTS) {
      assert.deepEqual(bridge.derivePublic(s.alg, s.sk), s.pk);
      const noble =
        s.alg === b.SLH
          ? Buffer.from(
              slh_dsa_shake_256s.sign(msg, s.sk, { extraEntropy: false }),
            )
          : b.sign(s.alg, s.sk, msg);
      const native = bridge.sign(s.alg, s.sk, msg);
      assert.equal(bridge.verify(s.alg, s.pk, msg, noble), true);
      assert.equal(b.verify(s.alg, s.pk, msg, native), true);
      assert.equal(b.verify(s.alg, s.pk, Buffer.from("tamper"), native), false);
      assert.equal(native.length, s.alg === b.ML ? 4627 : 29792);
      assert.equal(noble.length, native.length);
      assert.equal(s.pk.length, s.alg === b.ML ? 2592 : 64);
      assert.deepEqual(native, noble); // Both use the FIPS deterministic signing mode.
    }
  },
);
test("noble fallback signs when OpenSSL is absent", { timeout: 180000 }, () => {
  const path = process.env.PATH;
  try {
    process.env.PATH = "";
    const msg = Buffer.from("BRTH fallback"),
      sig = b.sign(b.SLH, ROOT.slh.sk, msg);
    assert.equal(sig.length, 29792);
    assert.equal(b.verify(b.SLH, ROOT.slh.pk, msg, sig), true);
  } finally {
    process.env.PATH = path;
  }
});
