# Codex follow-up #5 — make the founder report reflect the MEASURED findings

## Context

The bounded benchmark finished and the evidence is complete for every phase
except the 100k scale step (being re-measured separately right now).

The measured numbers are much stronger for the static profile than the
auto-generated report currently claims. The report prose is a static template
inside `generate_static_report_markdown(...)` and it was written before the
final numbers existed, so several verdicts are now stale or understated.

Files you own for this task:

- `experimental/punkti-v0.6-static/src/staticpub/bench.py` (the markdown
  generators only)
- `experimental/punkti-v0.6-static/tests/test_static_publication.py`
  (only ADD tests; never weaken or delete existing ones)

Do NOT change the publisher, reader, store, carrier, `run_scale_100k`,
`run_all`, or any protocol/semantic behaviour. Do not commit. Do not push.

## The measured facts the report must reflect

Read them from `evidence/bench_static.json` and `evidence/bench_mesh.json` —
never hardcode a number; derive every figure from the evidence at render time.

### 1. Request-count collapse is the headline finding (mode B / packs)

At 5,000 atoms, `fresh_subscriber_allspace`:

| | requests | transferred bytes |
|---|---:|---:|
| static A (index-only) | 5,005 | 1,825,045 |
| static B (packs) | 26 | 1,846,765 |

That is ~192× fewer requests for ~1.2% more bytes. At 1,000 atoms the same
ratio holds (1,005 → 11 requests). The current report says only "mode B
remains a latency optimization option in selected scenarios, while mode A
usually keeps transfer bytes lower" — that is now **wrong**: mode A does NOT
keep transfer bytes meaningfully lower, and mode B is not merely a latency
option, it is the profile that makes bootstrap practical.

State the request-count ratio explicitly, and state the byte overhead
explicitly, in section 7.

### 2. Mesh vs static: distinguish REQUEST COUNT from WALL TIME

Mesh wins on wall time in this loopback pass (5k fresh: mesh 4.935s vs static
B 21.255s), but Mesh's advantage is that it serves bytes from a live daemon
with a range-pull API. On the metric that actually matters for a dumb static
origin — number of HTTP requests to fill a fresh subscriber — static B wins
by a wide margin (26 requests vs Mesh's 157 pull requests at 5k).

Do NOT let section 8 read as "static loses". It must state both dimensions
honestly and note that the wall-time gap is measured against a stdlib
single-threaded static file server on a 1-vCPU host, which is not the same
as a CDN/CDN-cached origin.

### 3. Storage amplification (new, from the completed run)

At 1,000 atoms: mode A publication 365,619 bytes over 1,005 files
(amplification 1.993×); mode B publication 553,537 bytes over 1,011 files
(amplification 3.018×). Rebuild wall: A 0.864s, B 0.390s.

Include this in section 7 — mode B costs ~3× storage but rebuilds faster
(because republishing reuses existing immutable objects instead of rewriting
per-record objects).

### 4. Concurrency (new, from the completed run)

At 1,000 atoms against ONE shared publication:

| mode | readers | aggregate requests | wall |
|---|---:|---:|---:|
| A | 1 | 1,005 | 5.997s |
| A | 8 | 8,040 | 31.271s |
| B | 1 | 11 | 4.151s |
| B | 8 | 88 | 19.600s |

Eight concurrent readers on the same publication cost 88 origin requests in
mode B versus 8,040 in mode A. Add this to section 7 — it is the strongest
origin-load argument in the whole experiment.

### 5. The leaf-depth sweep

Recommended leaf depth is **2** (lowest combined median requests; depth 10 is
much worse — request score 5,664 vs 1,358 at depth 2). Mention the sweep's
shape in the report: shallower leaves mean fewer index objects and fewer
requests.

### 6. Mutable-file accounting (Issue #20 explicitly asks for it)

Issue #20 asks to record "number/size of mutable files". The raw runs already
carry `mutable_files: {'count': 1, 'bytes': 150}` — a single 150-byte
`root.json` is the only mutable file; everything else is content-addressed
and immutable. Surface this in the report (section 1 and/or 2), because it is
direct evidence for "only the minimum discovery pointer may change
frequently".

### 7. Section 10 and 11 must be concrete, not generic

Section 10 ("what dynamic Mesh mechanisms become unnecessary") and section 11
("what the current Mesh still does materially better") currently list three
and two generic bullets. Rewrite them against the measured evidence:

- Section 10 must name the mechanisms the static profile removes the
  *correctness* need for (PUSH endpoint, dynamic range-query API,
  reciprocal callback/session state, live daemon at the serving side) AND
  state the condition under which they remain useful (accelerators).
- Section 11 must state honestly what Mesh still does better: lower wall
  time in this loopback pass, one-shot range pull, no publication rebuild
  step, simpler incremental catch-up, and the fact that Mesh's pull requests
  are dynamic-range rather than per-object.

### 8. Section 12 recommendation

Keep the three-way framing the Issue asks for (adopt static-first / keep
dynamic Mesh normative / hybrid with a sharply defined optional accelerator).
Do NOT simply hardcode "hybrid" as a constant string any more — derive the
recommendation from the measured evidence where the evidence supports it, and
at minimum justify it explicitly against the measured numbers. If you keep
"hybrid", the report must say exactly what the accelerator is and what the
normative correctness path is.

Also keep the report's "Limitations (explicit)" list and ADD:
- the 1-vCPU / 2 GB host constraint;
- the fact that the 100k scale step's outcome depends on the budget and must
  be read from the evidence (`scale_100k.completed` / `reason`), not assumed.

## Rendering rules

- Every number in the report must come from the evidence JSON at render time.
  No hardcoded figures in the generator.
- If a phase is missing or truncated, render it as "not completed" with the
  reason — never as 0 or as a blank that reads like a real measurement.
- Keep the 12-section structure and its current headings.
- The report must remain readable as a standalone document for the Founder.

## Tests

Add fast tests proving:
- the rendered report contains the mode-A-vs-mode-B request-count ratio and
  the byte-overhead percentage derived from the evidence;
- the rendered report contains the concurrency rows for 1 and 8 readers for
  both modes;
- the rendered report names the mutable-file count/bytes;
- the rendered report still renders correctly (and says "not completed" with
  the reason) when the scale step is truncated or missing;
- the rendered report does NOT contain a hardcoded literal figure for the
  request ratio (i.e. it changes when the evidence changes).

Keep all 29 existing tests untouched and green.

## Stop condition

Report: files changed, test counts before/after, and the new section-7/
8/10/11/12 wording you generated (paste the rendered text of those sections
from a real `regenerate_docs_from_evidence()` call against the CURRENT
evidence files). Do not commit. Do not push.
