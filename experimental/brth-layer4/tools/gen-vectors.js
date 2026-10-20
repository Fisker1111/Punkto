"use strict";
const fs = require("node:fs");
const path = require("node:path");
const b = require("../src");
// Published BIP-39 test entropies: all zero bits and all one bits. TEST ONLY.
const root = [],
  birth = [];
for (const fill of [0, 255]) {
  const r = b.deriveRootKeys(Buffer.alloc(32, fill)),
    obj = b.buildBirth(r);
  root.push({
    testCase: fill === 0 ? "BIP39-all-zero-256" : "BIP39-all-one-256",
    mlPkHex: r.ml.pk.toString("hex"),
    slhPkHex: r.slh.pk.toString("hex"),
  });
  birth.push({
    testCase: root.at(-1).testCase,
    cjsonHex: b.encode(obj).toString("hex"),
    identity_id: b.identityIdOf(obj),
  });
}
for (const [name, cases] of Object.entries({ root, birth }))
  fs.writeFileSync(
    path.join(__dirname, "../vectors", name + ".json"),
    JSON.stringify({ warning: "TEST-ONLY-NOT-A-SECRET", cases }, null, 2) +
      "\n",
  );
