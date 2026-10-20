"use strict";
const { fields, b32, clone } = require("./format");
const { digest } = require("./cjson");
const { ML, SLH, validateKey } = require("./keys");
function validateRoot(root) {
  fields(root, ["threshold", "keys"]);
  if (
    root.threshold !== 2 ||
    !Array.isArray(root.keys) ||
    root.keys.length !== 2
  )
    throw Error("root quorum");
  root.keys.forEach(validateKey);
  if (root.keys[0].alg !== ML || root.keys[1].alg !== SLH)
    throw Error("root suite/order");
}
function validateBirth(obj) {
  try {
    fields(obj, ["type", "v", "suite", "root"]);
    if (obj.type !== "brth.birth" || obj.v !== 1 || obj.suite !== "BRTH-1")
      throw Error("birth constants");
    validateRoot(obj.root);
    return { ok: true, errors: [] };
  } catch (e) {
    return { ok: false, errors: [e.message] };
  }
}
function buildBirth(r) {
  const keys = Array.isArray(r)
    ? r
    : [
        { alg: ML, pk: Buffer.from(r.ml.pk).toString("base64url") },
        { alg: SLH, pk: Buffer.from(r.slh.pk).toString("base64url") },
      ];
  const b = {
    type: "brth.birth",
    v: 1,
    suite: "BRTH-1",
    root: { threshold: 2, keys },
  };
  const v = validateBirth(b);
  if (!v.ok) throw Error(v.errors.join());
  return clone(b);
}
function identityIdOf(b) {
  const v = validateBirth(b);
  if (!v.ok) throw Error(v.errors.join());
  return "b1:" + b32(digest(b));
}
module.exports = { buildBirth, identityIdOf, validateBirth, validateRoot };
