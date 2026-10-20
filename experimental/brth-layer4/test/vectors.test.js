"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const b = require("../src");
test("root public keys and Birth bytes match committed published-seed vectors", () => {
  const roots = require("../vectors/root.json").cases,
    births = require("../vectors/birth.json").cases;
  for (const [i, fill] of [0, 255].entries()) {
    const r = b.deriveRootKeys(Buffer.alloc(32, fill)),
      birth = b.buildBirth(r);
    assert.equal(r.ml.pk.toString("hex"), roots[i].mlPkHex);
    assert.equal(r.slh.pk.toString("hex"), roots[i].slhPkHex);
    assert.equal(b.encode(birth).toString("hex"), births[i].cjsonHex);
    assert.equal(b.identityIdOf(birth), births[i].identity_id);
  }
});
test("Birth rejects unknown fields, wrong types, downgrade and root order", () => {
  const { BIRTH } = require("./helpers");
  for (const obj of [
    { ...BIRTH, extra: 1 },
    { ...BIRTH, v: "1" },
    { ...BIRTH, root: { ...BIRTH.root, threshold: 1 } },
    { ...BIRTH, root: { ...BIRTH.root, keys: [...BIRTH.root.keys].reverse() } },
  ])
    assert.equal(b.validateBirth(obj).ok, false);
});
