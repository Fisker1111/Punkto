# CODEX_TASK_22 — STAGE 5 (MID as exact link identity + legacy `p:` quarantine)

Read `docs/CODEX_TASK_22.md` first (full contract), then `docs/CODEX_TASK_22_STAGE3.md`
and `docs/CODEX_TASK_22_STAGE4.md`. Stages 3 and 4 MUST keep passing.

**Do not commit. Do not push. Do not deploy. Do not build or push any Docker image. Do not
touch any server.**

---

## Stage 5 goal

Fix a **defect found in independent review** of the Stage 3/4 working tree.

Stage 3 made the browser read atoms from the static publication, where the record's
identity is the **MID** (`punkti/0.6:<64 hex>`). It set that MID as the atom's
`atom_id`:

```js
// pwa/sync/punkti-client.js — mapRecordToAtom
atom_id: record.mid,
mid: record.mid,
```

But the rest of the PWA still assumes `atom_id` is the **legacy 64-hex stable atom id**
(`pwa/protocol/atom-id.js`):

```js
export function isStableAtomId(value) {
  return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
}
```

The two formats are incompatible, and the consequences are real.

### Confirmed breakage (reproduce it before fixing it)

```bash
cd /home/hermes/.hermes/kanban/workspaces/t_3d146aba/punkto
node --input-type=module -e '
import { canonicalAtomPath, canonicalAtomUrl, parsePublicPPath } from "./pwa/protocol/exact-link.js";
const mid = "punkti/0.6:" + "a".repeat(64);
console.log("path:", JSON.stringify(canonicalAtomPath(mid)));
console.log("url :", JSON.stringify(await canonicalAtomUrl(mid)));
console.log("parse:", JSON.stringify(parsePublicPPath("/p/" + encodeURIComponent(mid))));
'
```

Observed (correct) current behaviour — **all broken**:

```
path: ""
url : ""
parse: null
```

Consequences in the product:

1. **Deep links are dead for every statically-read atom.** `canonicalAtomPath` returns
   `""`, so `canonicalAtomUrl` returns `""`.
2. **PDF / QR export carries no URL.** `pwa/print-pdf.js` → `qrPayloadForAtom` /
   `generatePunktiPdfBytes` both go through `canonicalAtomUrl`, so the QR payload and
   the PDF's printed link are **empty strings** for static-read atoms.
3. **Map deep-link focus mis-resolves.** `pwa/ui-map.js` (~line 263) falls back to
   `ensurePunktoPrefix(rawId)`, which for a MID yields the nonsense value
   `p:punkti/0.6:aaaa…` — a "Punkto ID" that is not one, and which
   `decodeAtomLocation` cannot decode, so the map cannot focus the atom.
4. **`parsePublicPPath` cannot parse a MID deep link at all**, so a MID URL never
   resolves to an atom.

### What the Issue requires

From CEO-OS Issue #22, Phase 4 (clean Layer 3 / Layer 4 boundary):

> MID becomes the natural exact logical object/link identity where an exact Punkti
> object reference is needed.

And Phase 4 also says:

> Do not retain old `p:<12-char-3D-geohash>` as a second quasi-protocol spatial
> identity.

So the fix is **not** "make MID look like a 64-hex id". The fix is to make **MID a
first-class exact link identity** in the deep-link / PDF / QR path, and to keep the
legacy `p:` form as a *frozen compatibility* form only — never as the 0.6 identity.

---

## S5.1 — Make MID a first-class exact link identity

Introduce a single, shared notion of "this atom's exact identity" and use it
everywhere an exact identity is needed.

1. Add a helper (choose the module — `pwa/protocol/atom-id.js` or a new
   `pwa/protocol/exact-identity.js`; state your choice) that recognises and validates
   the frozen Punkti 0.6 MID form. The frozen form is exactly:
   `punkti/0.6:<64 lowercase hex>`. It MUST match the frozen carrier's own definition
   — read `pwa/punkti/carrier.js` (see `MID_PREFIX` / the `address` it emits) and
   `experimental/punkti-v0.6-publication/vectors.json` and **derive the exact regex
   from the frozen contract**, not from this prose. Do not invent a looser form.

2. `pwa/protocol/exact-link.js`:
   * `canonicalAtomPath(atomOrId)` MUST return a working path for a MID-valued id.
   * `canonicalAtomUrl(atomOrId, origin)` MUST return a working absolute URL for a
     MID-valued id.
   * `parsePublicPPath(pathname)` MUST parse a `/p/<MID>` deep link back to that atom.
   * `canonicalAtomId(atom)` — keep it, but make it resolve the **exact** identity:
     if the atom carries a valid MID, return it; otherwise keep the existing
     64-hex stable-id computation for legacy atoms.

3. **Path encoding.** A MID contains `:` and `.` (`punkti/0.6:…`) but **no `/`**, so it
   is safe in a `/p/<segment>` path. Confirm that and use `encodeURIComponent`
   consistently on the way out and `decodeURIComponent` on the way in. Verify a
   round-trip: `parsePublicPPath(canonicalAtomPath(mid))` returns the same MID.

4. **Precedence.** When an atom carries **both** a MID and a legacy id, the **MID
   wins** for exact-identity purposes (deep link, PDF/QR, exact object reference).
   The legacy `p:` / 64-hex id may still be accepted on input for **backwards
   compatibility** with already-shared links, but the canonical outbound form MUST be
   the MID.

5. **Keep the legacy path working.** Existing `/p/<64-hex>` and `/p/<p:12-char>` links
   must still resolve (frozen v0.5.1 history is preserved). Do not break them.

---

## S5.2 — Fix the map focus path

`pwa/ui-map.js` (~line 255-275) must resolve a deep link to an atom when the id is a
MID:

* the lookup must find the atom whose `mid` (or `atom_id`) equals the requested id;
* the `punkto` fallback must NOT produce `p:punkti/0.6:…`. When the focused atom has a
  valid `h` (XY_Z), derive the map position from **`h`** (the Layer-3 truth), not from
  the legacy `p:` string;
* the map must still be able to focus a MID deep link end-to-end.

Note `pwa/core/location.js` already gained `h` (XY_Z) decoding in Stage 3 — reuse it
rather than adding another decoder.

---

## S5.3 — Legacy `p:` quarantine

The Issue requires that the legacy `p:<12-char-3D-geohash>` form is **not** a second
quasi-protocol spatial identity in the 0.6 path, while frozen v0.5.1 history stays
where compatibility needs it.

1. `pwa/sync/punkti-client.js` currently derives a legacy address from the 0.6 `h`:
   ```js
   function deriveLegacyPunkto(h) { … return parsed ? `p:${parsed.xy}` : ''; }
   ```
   Note this produces `p:<xy>` — a **2D geohash** wearing the `p:` prefix of a form
   that was always a **3D** geohash. That is a third, wrong identity shape: it is not
   a valid legacy `p:` id (`BARE_ID_RE` expects 12 chars) and it is not the 0.6 `h`.
   Replace it with an explicit, honest approach:
   * the atom's canonical spatial truth is `h` (XY_Z) — always;
   * the legacy `punkto` field should either be **left empty** for 0.6-native atoms, or
     be populated by a clearly-labelled compatibility derivation that is a **valid**
     legacy id or **nothing at all**. Do not fabricate a malformed `p:` id.
   * Whatever you choose, the UI must not present it as the atom's spatial identity
     where `h` is available.

2. Grep the tree for other producers of malformed `p:` values from 0.6 data and fix
   them the same way.

3. Do **not** delete the legacy v0.5.1 code paths (`pwa/geohash3d.js`,
   `pwa/protocol/punkto-id.js`, the `p:` deep-link parsing, the legacy
   `decodeAtomLocation` fallback). They are the frozen compatibility form.

---

## S5.4 — Regression tests (must be real, must fail before the fix)

Add a focused test file (e.g. `pwa/test-exact-identity.mjs`) that asserts:

1. `canonicalAtomPath(mid)` returns a non-empty path for a valid MID.
2. `canonicalAtomUrl(mid, origin)` returns an absolute URL containing the MID.
3. `parsePublicPPath(canonicalAtomPath(mid))` round-trips to the same MID.
4. A MID deep link resolves to the atom (via the same lookup the map uses).
5. Legacy `/p/<64-hex>` and `/p/<p:12char>` links STILL parse (backwards compat).
6. An invalid MID (wrong prefix, wrong hex length, uppercase hex, a 64-hex id with no
   `punkti/0.6:` prefix) is **rejected** — not silently accepted.
7. `pwa/print-pdf.js`'s QR payload for a MID-valued atom is a **non-empty** URL that
   contains the MID.

Write the test so that it **fails on the pre-fix tree** (it does today) and passes
after the fix. Show both runs' real output in the evidence.

Also extend the Playwright E2E (`pwa/test-punkti-static-e2e.mjs`) so the real-PWA
scenario asserts that a statically-read atom produces a **working deep link** and a
**non-empty QR/PDF URL**. If the Stage 4 real-PWA test exists, add the assertion
there; if not, add a module-level assertion and say so.

---

## S5.5 — Checks that must pass before you report done

```bash
cd /home/hermes/.hermes/kanban/workspaces/t_3d146aba/punkto

for f in pwa/*.js pwa/*/*.js; do node --check "$f" || exit 1; done
node --input-type=module --check < pwa/app.js

node pwa/test-exact-identity.mjs
node pwa/test-punkti-vectors.mjs
node pwa/test-punkti-publication.mjs
node pwa/test-spatial-xy-z.mjs
node pwa/test-slice5.mjs

PLAYWRIGHT_MODULE="file:///home/hermes/.npm/_npx/420ff84f11983ee5/node_modules/playwright/index.mjs" \
  node pwa/test-punkti-static-e2e.mjs

python3 -m unittest punkti_node.test_node punkti_node.test_web punkti_node.test_publication
python3 -m unittest discover -s experimental/punkti-v0.6-mesh/tests
python3 -m unittest discover -s experimental/punkti-v0.6-publication/tests

bash -n scripts/acceptance_static_first.sh
```

Plus the YAML lint of every workflow and example config you touched.

All must exit 0.

---

## S5.6 — Update the integration report

Update `docs/INTEGRATION_22.md`:

* §1 (legacy code removed / retained) — describe the legacy `p:` quarantine decision.
* Add a short section documenting the **exact identity model** now in force: MID is the
  exact link identity; the legacy 64-hex id and `p:` form are frozen compatibility
  inputs only.
* §5 acceptance table — add a row for the MID exact-link identity criterion with PASS
  and the evidence file.
* §6 — add the new evidence files.
* §7 — refresh the open-gates list if this changes the cutover recommendation.

Put the raw output of every command in §S5.5 under `docs/evidence/issue-22/` with
descriptive filenames. Nothing fabricated; every NOT RUN keeps a concrete reason.

---

## S5.7 — Report

1. Files changed/added/deleted.
2. Real output of every command in §S5.5, plus the **before/after** proof that the new
   test fails on the pre-fix tree.
3. The updated acceptance table.
4. Confirmation: nothing committed, nothing pushed, no image built or pushed, no
   deployment, no server touched.

## S5.8 — Spec-first rule

If you find a genuine contradiction in the frozen normative contracts, **STOP and report
it with a concrete counterexample** instead of guessing. Derive the exact MID form from
the frozen carrier/vectors — do not weaken the check to make it pass.
