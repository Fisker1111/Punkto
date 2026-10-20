"use strict";
const words = require("./wordlist-en");
const { createHash, randomBytes } = require("node:crypto");
function entropyToWords(entropy) {
  if (!(entropy instanceof Uint8Array) || entropy.length !== 32)
    throw Error("32-byte entropy");
  const bits = Array.from(
    Buffer.concat([
      entropy,
      createHash("sha256").update(entropy).digest().subarray(0, 1),
    ]),
    (b) => b.toString(2).padStart(8, "0"),
  ).join("");
  return bits
    .match(/.{11}/g)
    .map((b) => words[parseInt(b, 2)])
    .join(" ");
}
function wordsToEntropy(phrase) {
  if (typeof phrase !== "string") throw Error("phrase string");
  const list = phrase.split(" ");
  if (list.length !== 24) throw Error("24 words required");
  const bits = list
    .map((w) => {
      const i = words.indexOf(w);
      if (i < 0) throw Error("unknown word");
      return i.toString(2).padStart(11, "0");
    })
    .join("");
  const entropy = Buffer.from(
    bits
      .slice(0, 256)
      .match(/.{8}/g)
      .map((b) => parseInt(b, 2)),
  );
  if (entropyToWords(entropy) !== phrase) throw Error("checksum");
  return entropy;
}
module.exports = {
  entropyToWords,
  wordsToEntropy,
  newWords: () => entropyToWords(randomBytes(32)),
};
