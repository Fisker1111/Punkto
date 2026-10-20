"use strict";
const { encode } = require("./cjson");
function fields(o, names) {
  if (
    !o ||
    typeof o !== "object" ||
    Array.isArray(o) ||
    Object.keys(o).length !== names.length ||
    Object.keys(o).some((k) => !names.includes(k))
  )
    throw Error("unknown/missing fields");
  encode(o);
}
function integer(n) {
  if (!Number.isSafeInteger(n) || Object.is(n, -0))
    throw Error("integer required");
}
function text(s) {
  if (typeof s !== "string") throw Error("string required");
}
function bytes(s, n) {
  text(s);
  const b = Buffer.from(s, "base64url");
  if (b.toString("base64url") !== s || (n !== undefined && b.length !== n))
    throw Error("binary encoding/length");
  return b;
}
function b32(b) {
  let acc = 0,
    bits = 0,
    out = "";
  for (const c of b) {
    acc = (acc << 8) | c;
    bits += 8;
    while (bits >= 5) {
      bits -= 5;
      out += "abcdefghijklmnopqrstuvwxyz234567"[(acc >>> bits) & 31];
    }
  }
  if (bits) out += "abcdefghijklmnopqrstuvwxyz234567"[(acc << (5 - bits)) & 31];
  return out;
}
function id(s, p = "b1:") {
  if (
    typeof s !== "string" ||
    !new RegExp("^" + p + "[a-z2-7]{51}[aq]$").test(s)
  )
    throw Error("identifier");
}
const clone = (o) => require("./cjson").decode(encode(o));
module.exports = { fields, integer, text, bytes, b32, id, clone };
