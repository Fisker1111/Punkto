"use strict";
const { createHash } = require("node:crypto");
const compare = (a, b) => {
  const x = Array.from(a, (c) => c.codePointAt(0)),
    y = Array.from(b, (c) => c.codePointAt(0));
  for (let i = 0; i < Math.min(x.length, y.length); i++)
    if (x[i] !== y[i]) return x[i] - y[i];
  return x.length - y.length;
};
function string(s) {
  if (!s.isWellFormed()) throw Error("lone surrogate");
  return JSON.stringify(s.normalize("NFC")).replace(/\\u00[0-9a-f]{2}/g, (s) =>
    s.toUpperCase().replace("U", "u"),
  );
}
function encode(value) {
  const seen = new Set();
  function visit(v) {
    if (v === null || typeof v === "boolean") return String(v);
    if (typeof v === "string") return string(v);
    if (typeof v === "number") {
      if (!Number.isSafeInteger(v) || Object.is(v, -0))
        throw Error("integer required");
      return String(v);
    }
    if (typeof v !== "object" || seen.has(v)) throw Error("invalid type/cycle");
    seen.add(v);
    let result;
    if (Array.isArray(v)) {
      if (
        Object.keys(v).length !== v.length ||
        Reflect.ownKeys(v).length !== v.length + 1
      )
        throw Error("sparse/extended array");
      result = "[" + Array.from(v, visit).join(",") + "]";
    } else {
      if (
        Object.getPrototypeOf(v) !== Object.prototype &&
        Object.getPrototypeOf(v) !== null
      )
        throw Error("plain object required");
      if (Reflect.ownKeys(v).length !== Object.keys(v).length)
        throw Error("hidden/symbol field");
      const keys = Object.keys(v),
        norm = keys.map((k) => k.normalize("NFC"));
      if (new Set(norm).size !== keys.length)
        throw Error("duplicate normalized key");
      result =
        "{" +
        keys
          .sort((a, b) => compare(a.normalize("NFC"), b.normalize("NFC")))
          .map((k) => {
            if (!("value" in Object.getOwnPropertyDescriptor(v, k)))
              throw Error("accessor");
            return string(k) + ":" + visit(v[k]);
          })
          .join(",") +
        "}";
    }
    seen.delete(v);
    return result;
  }
  return Buffer.from(visit(value), "utf8");
}
function decode(buf) {
  if (!(buf instanceof Uint8Array)) throw Error("bytes required");
  const raw = Buffer.from(buf),
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
      raw,
    );
  const value = JSON.parse(text);
  // Re-encoding also rejects duplicate members, alternate escapes, numbers and whitespace.
  if (!encode(value).equals(raw)) throw Error("non-canonical CJSON");
  return value;
}
const digest = (value) => createHash("sha3-256").update(encode(value)).digest();
module.exports = { encode, decode, digest };
