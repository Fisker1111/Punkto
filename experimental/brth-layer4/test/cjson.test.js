"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const { encode, decode, entropyToWords, wordsToEntropy } = require("../src");
test("CJSON code point order, NFC, required escapes and round trip", () => {
  const obj = {
    "😀": 1,
    "\ue000": 2,
    z: "e\u0301",
    a: '\x00\x0b\b\f\n\r\t"\\',
    n: [null, true, false, 9007199254740991, -9007199254740991],
  };
  const s = encode(obj).toString();
  assert.ok(s.indexOf("\ue000") < s.indexOf("😀"));
  assert.ok(s.includes("é"));
  assert.ok(s.includes("\\u000B"));
  assert.deepEqual(encode(decode(encode(obj))), encode(obj));
});
test("CJSON rejects floats, duplicates, invalid Unicode, types and noncanonical bytes", () => {
  for (const x of [
    1.2,
    NaN,
    Infinity,
    -0,
    2 ** 53,
    undefined,
    1n,
    () => 0,
    new Date(),
    [, ,],
    { é: 1, "e\u0301": 2 },
    "\ud800",
  ])
    assert.throws(() => encode(x));
  for (const s of [
    '{"x":1,"x":2}',
    '{"z":1,"a":2}',
    "1.0",
    "1e0",
    "-0",
    "01",
    "+1",
    "NaN",
    " true",
    '"e\\u0301"',
    '"\\u0061"',
    '"\\ud800"',
    '"\\u000b"',
  ])
    assert.throws(() => decode(Buffer.from(s)));
  assert.throws(() => decode(Buffer.from([0xff])));
  assert.throws(() => decode(Buffer.from("\ufeff{}")));
});
test("BIP39 published zero/one vectors, checksum and 23/25 words", () => {
  const cases = [
    [0, Array(23).fill("abandon").concat("art").join(" ")],
    [255, Array(23).fill("zoo").concat("vote").join(" ")],
  ];
  for (const [n, words] of cases) {
    assert.equal(entropyToWords(Buffer.alloc(32, n)), words);
    assert.deepEqual(wordsToEntropy(words), Buffer.alloc(32, n));
  }
  for (const words of [
    Array(24).fill("abandon"),
    Array(23).fill("abandon"),
    Array(25).fill("abandon"),
    Array(24).fill("unknownword"),
  ])
    assert.throws(() => wordsToEntropy(words.join(" ")));
  assert.equal(require("../src/wordlist-en").length, 2048);
});
