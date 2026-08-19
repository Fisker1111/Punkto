# OpenRouter Model Fusion — Candidate 5

> Fused design review of Candidate 5 ("The Craigslist, Light 3D") as a child of Candidate 4 ("The Living Public World").
> Panel: four independent reviews, then fused. Consensus, majority and minority positions are labelled; real disagreement is preserved, not averaged. Product architecture is kept separate from visual styling throughout.

## 1. Executive verdict

Candidate 5 is the right launch discipline and, as written, the wrong constitutional boundary — and all four panel members independently reached the verdict COMBINE. C5's diagnosis is accepted unanimously: C4 as specified is effectively unshippable by a small open-source team (its own spec concedes this), its warmth risks being purchased with asset pipelines that would kill the self-hosting mandate, and its central mechanism — semantic zoom from region patterns to one conversation — is density-dependent and therefore untestable at launch, since a village with three atoms has nothing to aggregate. C5 supplies the enforcement mechanism C4 lacked: a reference-device budget, one build with no fallback tier, no asset downloads, no server-side content dependencies. But C5 makes three errors that would, if it stood alone as v1's constitution, quietly foreclose its parent: it risks freezing surfaces where it should freeze semantics (frozen pixels foreclose C4; frozen meaning makes C4 reachable as a theme); it treats warmth as a graphics budget when most warmth is microcopy, typography, empty states, easing and one restrained procedural glow — costing zero bytes and negligible milliseconds; and it rests doctrine 3 on the least reliable mechanism in open source, community pull requests supplying foundational experience work. Adopt C5's discipline as Punkto's v1 shipping posture, on condition that it absorbs C4's non-delegable kernel semantics (typed relations, validity/expiry, altitude datum and positional uncertainty, an aggregate-query contract, one-camera/axis rule, a non-suppressible urgency channel) and ships a cheap first-party warmth floor rather than delegating the product's soul.

## 2. Scores

Fused 1–5. Where the panel split materially, the range is shown and the split is named.

| Dimension | Score | Reason |
|---|---|---|
| Clarity | 5 | Unanimous. Three "lights" (client/server/governance) is the crispest, most falsifiable doctrine any candidate has produced; instantly communicable to contributors. |
| Desirability | 3 | Unanimous. Respected rather than longed-for; "a tool that wants to be closed" earns trust but not attachment, and will be read as unfinished by some regardless of honesty. |
| Punkto uniqueness | 4 (range 3–5) | Uniqueness lives in p: addressing + altitude + no engagement machinery, not in the render — but collapses toward "another map app" if the beacon or true 3D is sacrificed to cheapness. |
| Social warmth | 2 | Unanimous, and the lowest score for a reason: warmth is not merely deferred, it is unspecified. C5 names the risk ("the beacon must still glow") and supplies no mechanism. |
| Practical usefulness | 5 | Unanimous. Handles all four required scenarios with margin; real utility on day one, unlike the north-star world. |
| Atom/thread clarity | 3.5 (range 3–4) | Flat boards keep reading legible, but C5 does not itself specify reply/confirmation/resolution relations — the hydrant scenario exposes the gap. |
| Mobile feasibility | 5 (one dissent at 4) | The doctrine's core strength. Minority note: a map PWA with spatial queries still needs measured budgets; "no performance budget meeting" must not mean "no measurement." |
| Self-hosting feasibility | 4 (range 4–5) | Highest of any candidate — but the spec is silent on basemap and media policy, which are what actually break first, not atom serving. |
| Delegation realism | 1.5 (range 1–2) | Unanimous and strongly held: contributions follow adoption and cluster at the periphery (themes, translations, packaging), never at foundational interaction design, accessibility or renderers. |
| Compatibility with C4's north star | 3.5 (range 3–4) | High if the freeze is semantic and cheap warmth ships in v1; low if "freeze the visual grammar early" means freezing the austere look itself. As written: ambiguous. |

## 3. Consensus findings

1. **Density, not rendering, is Punkto's launch constraint.** C4's semantic zoom is inert below a density threshold Punkto will not reach for years. C5 designs for the condition that will actually exist, and the honest rendering of a near-empty world is a fast one.
2. **C5 illegitimately bundles two independent "light" arguments.** Client GPU cost is paid by the viewer's phone; server cost is paid by the operator. A procedural client glow costs the operator exactly nothing. The doctrine's real, defensible content is no server-side content or asset dependencies — no tile servers, no required media hosting, no GPU assumptions — not "richness is expensive for operators." Rewrite it that way.
3. **Rendering will not be what breaks first on a home server.** In rough order: the basemap/tile dependency (or the third-party key's quota, ToS and viewport leakage); media storage and re-encoding if atoms carry attachments; reachability operations (CGNAT, dynamic DNS, TLS renewal); query amplification during exactly the burst the urgent scenario creates; moderation and legal exposure for a private individual hosting geo-anchored claims about neighbours' property; key loss; operator burnout. Fediverse evidence is consistent: small instances die of cost, moderation load and burnout, not of missing features, while a full ActivityPub server runs in ~250–350 MB RAM on a €2–5 VPS or single-board computer. Atom serving is never the bottleneck. Scale asymmetry underlines the point: OSM's tile CDN served roughly 1.4 PB and 121 billion requests in a single month — atoms will never be that; pixels can be.
4. **"Warmth is expensive" is C5's clearest category error.** Tone of voice, authored empty states, restrained palette, easing curves, one soft glow, a pulse derived deterministically from timestamps, and the decision not to show a scoreboard are all warmth, and all essentially free. C5 could be the warmest candidate at 60 fps on a 2019 phone. Further: in a system with no likes, counts or feeds, liveness cues are the only remaining channel that signals "people were here recently." Deleting warmth without replacing that signalling function leaves a dead database with good latency — obeying C4's letter while breaking its promise.
5. **Freeze semantics, not surfaces.** Freeze the wire format, atom/relation/coordinate/altitude semantics, camera and axis rules, ordering rules, query and aggregate contracts. Do not freeze palette, glow, shaders, or the austere aesthetic. C4's own epistemics ("earn the vision through usage evidence") forbid freezing a visual grammar nobody has used yet — hence a two-speed freeze: wire hard now, visual grammar explicitly versioned and marked provisional for 6–12 months.
6. **Semantic zoom is a data contract, not a style choice.** An aggregate/summary query (bbox+zoom → counts/centroids, provenance and freshness visible) must be specified now even if implemented naively in-process. It is the single cheapest thing that keeps C4 reachable without a protocol break. Aggregates are projections over atoms, never authoritative replacements — decorative aggregates must never mask sparse data.
7. **Urgency must be kernel-level semantics, non-suppressible by any theme.** If themes may change colour and urgency is signalled by colour, delegation silently destroys the one signal that matters, and two clients render the same flood differently — breaking one authoritative spatial context. Required: a declared atom kind with a mandatory expiry, redundant text/icon/shape meaning, and a protected signalling channel.
8. **The hydrant scenario breaks C5 as written.** It needs a small closed vocabulary of typed relations — reply-to, confirms, disputes, supersedes/resolves — plus a derivation rule producing displayed state ("3 confirmations, unresolved, 11 days"). Attestation is not engagement: a confirmation is a claim about the world; a like is a claim about a message. Counting witness statements is legitimate; counting approval is forbidden by construction, because no such verb exists in the vocabulary. Retrofitting relation semantics into a deployed signed-event protocol is notoriously painful — Nostr's thread markers are still contested years on.
9. **Delegation as specified will fail.** More than 88% of GitHub projects have fewer than 16 core developers; 57% of sampled projects have a truck factor of one; only 41% recovered maintenance after losing key developers. Worse, community richness in this ecosystem historically arrives as hard forks (Glitch-soc, Misskey, Akkoma), not merged PRs — which means "community-owned richness" defaults to grammar fragmentation, the exact opposite of C4's one authoritative context. Permissive extension surfaces also collapse client ecosystems rather than growing them.
10. **Therefore delegation must be engineered, not hoped.** The core team must ship the scaffolding itself: documented extension points, theme tokens, at least one reference theme exercising every hook, a published conformance suite, versioning and deprecation policy, security review, and continued first-party ownership of the baseline experience and the C4 direction.
11. **Light must never mean flat.** The honest temptation of "lightest 3D" is 2.5D pins on a flat map — which would breach the parent's hardest rule. Tilted-camera true 3D costs almost nothing in draw calls. The freeze must explicitly forbid flattening.
12. **The sub-20-second urgent post is architecture C5 has not yet stated.** Twenty seconds on a mid-2019 Android over congested 4G is consumed by GPS fix, permissions, key access and retries. Required rules: compose must not depend on map or scene load; sign locally; record explicit positional uncertainty; queue offline with retry; no login wall. Cheapest honest urgency is subtractive — draw fewer things, larger, with motion.
13. **"One build, no fallback tier" is a genuine strength** that reinforces C4's one-authoritative-context rule: no fallback tier means no second grammar can exist.
14. **Time-to-look-up alone is an insufficient success metric.** It must be supplemented by comprehension and urgency-recognition gates and at least one ambient signal (return visits with no notification of any kind), while engagement metrics remain explicitly forbidden.
15. **V1 teaches the category.** Nobody knows what public atoms in space are. Speed is not the first impression; the glowing beacon at a place you recognise is. A light v1 is acceptable only if the differentiating magic — spatial anchoring, altitude, the pillar — is legible in the cheap render.

**Where C5 misreads C4 (consensus).** The metric swap is a product swap: time-to-look-up re-centres the product from place to task, invites an errand-shaped product that drifts toward the forbidden GIS console, and devalues stumbling — which is precisely how a sparse world's few atoms get found. "Wants to be closed" contradicts "faintly alive" and will teach the v1 community that later ambient value is mission drift. "Freeze the visual grammar early" is ambiguous in a way that could freeze the light look. And at the ecosystem level, unconstrained community pillar shaders or rich-world forks could make pillar height read as popularity, urgency or reply depth, or introduce competing projections and miniature scenes — killing vertical-equals-altitude and the anti-dollhouse rule even though every individual build looks fine.

**Where C4 is wrong and C5 is right (consensus).** C4 is unshippable as specified and admits it, with a phasing sentiment and no enforcement mechanism; C5 supplies the mechanism. C4 underestimates federation economics, which are existential for a self-hosted public square. C4's asset-fed warmth manufactures its own dollhouse risk, while constraint-first rendering forces clarity over decoration. C4 never resolves the contradiction between a viewer-first interface and an author-first launch; C5 resolves it in favour of the only population present at t=0. And one build for all devices is strictly better protocol hygiene than a tiered world.

## 4. Disagreements (preserved)

### D1 — Recommended posture: (a) or (b)?

Held strongly on both sides; this is the panel's real split, 3–1 for (b).

- **For (a) — C5 as v1 constitution, C4 as community north star and theme space (minority, held strongly):** C4 is not a later phase; C4 is a theme. Naming C5 the constitution is what makes the austerity binding; calling it "merely a phase" is exactly how C4's ambitions re-enter as mandatory complexity and the light build dies before shipping. Craigslist's history is honest precedent: it never got richer, and that was fine, because value was listing density, not interface. C5's real bet is density — say so.
- **For (b) — C5 merged into C4 as a strengthened phasing/shipping section (majority, held strongly):** Two documents with two souls manufactures the two-product split. Craigslist is the doctrine's own warning, not its licence: decades of success, zero acquired warmth, and a community that experiences any enrichment as bloat and forks to preserve the light product. You cannot swap a product's soul after adoption. Constitutions should protect semantics and interoperability, never impose a permanent rendering ceiling; an austerity constitution makes later course correction politically difficult. One identity, shipped under C5's discipline.
- **Counter-argument to (b), from the (a) camp and conceded by the (b) camp:** the merge's named risk is that C4's ambition re-inflates v1 once both doctrines share one document. The defence is that the reference-device budget and conformance suite are artifacts, not intentions — they hold the line even when prose doesn't.

### D2 — Which presentation keeps a newcomer in a three-atom village?

Majority C5, held moderately to strongly; one dissent held weakly.

- **C5 (majority):** an empty warm world reads as a ghost town — eerie, broken, and the most likely route to the exact dollhouse failure C4 forbids. An empty honest board reads as a young utility, which is normal; small-town Craigslist is sparse and fine.
- **C4 (minority, weak):** a sparse utilitarian map looks dead, while a faintly alive aesthetic makes three atoms feel like a beginning rather than an ending; because nobody yet understands spatial atoms, a bare map may read as an abandoned prototype.
- **Fused position:** C5's speed and candour plus a first-party warm sparse composition — legible local geography, all three beacons noticeable, immediate board preview, one concise sentence of category explanation. Density must never be faked.

### D3 — Should the basemap exist at all?

Genuine three-way split; unresolved and important.

- **No basemap (minority, held strongly):** the ground should be procedural and atom-derived — the world is the atoms on abstract terrain. This removes the biggest operator dependency, dodges the GIS-console trap, and increases uniqueness in one move.
- **Legible geography is a requirement (opposing view, held strongly):** "the bench by the canal" is meaningless without the canal, the street and orientation. Punkto needs a provider-neutral basemap contract covering attribution, privacy, caching and degraded operation — and honesty about what "fully self-hosted" means when map data comes from elsewhere.
- **Budget it, don't wish it away (middle):** prebuilt vector tiles are viable on Pi-class hardware (client-side styling; roughly 10–20 GB and 4 GB RAM for a city region; ~120 GB for a whole-world Protomaps file). Third-party tiles are simplest but re-centralise the stack and leak every viewer's viewport.

### D4 — Must semantic zoom appear in v1 in some form?

Majority yes-in-degenerate-form, held moderately.

- **Defer entirely (minority):** with three atoms, region patterns are meaningless, and kernel-team time is the scarce resource.
- **Freeze the ladder's semantics, ship a cheap tier (majority):** if the tiers are absent from the frozen grammar, adding them later is a breaking interaction change every theme and fork must absorb — the exact instability C5's governance doctrine exists to prevent. Minimum: freeze what becomes meaningful at each scale plus continuity rules, ship the aggregate endpoint naively, do not freeze shader implementations or permanent pixel thresholds.

### D5 — Does urgency deserve privileged prominence at all?

Majority yes-with-constraints (moderate); minority no-until-governed (held strongly).

- **Yes:** safety information must be noticeable; freshness and declared urgency are properties of the world, not engagement metrics.
- **No, not yet:** self-declared urgency is gameable, and if prominence affects discovery it becomes attention ranking by another name. Withhold any privileged class until abuse resistance and moderation governance are proven.
- **Fused:** ship it, but only with mandatory expiry, provenance, kernel-level delist/precision-blur moderation tools, local scoping, and federation propagation of removals.

### D6 — Should rendering be absolutely identical on every device?

Majority: one semantic build with bounded presentational reduction (moderate); minority: strict uniformity (moderate).

- **Strict:** no fallback tier means no second grammar, and low-end users are never second-class.
- **Bounded adaptation:** refusing all adaptation lets the weakest device permanently define the aesthetic, and C5 leaves undefined what happens on a phone that cannot hold the map open while composing. Adaptation may change detail, never meaning.

## 5. What the kernel must freeze now

### A. Protocol and atom semantics — hard freeze.

1. Canonical `p:<spatial>-<id>` form; precision/length semantics of the spatial component; an explicit privacy/precision rule (a bench and a front door must be expressible at different precisions).
2. Altitude contract: stated datum (WGS84 ellipsoidal vs orthometric/geoid), AGL-vs-AMSL discrimination, units, rounding — plus a mandatory positional/altitude uncertainty field. "Exact" must not conceal unreliable phone altitude.
3. Signed-atom identity: immutable id, author key, created-at, place, signature scheme; correction, supersession, retraction and tombstone behaviour.
4. Validity/expiry windows. Without ranking, recency-and-validity is the only legitimate ordering, so it must be kernel, not client.
5. Closed relation vocabulary: replies-to, confirms, disputes, supersedes/resolves, plus the derivation rule turning relations into displayed state. Attestation counts permitted; approval counts structurally impossible.
6. Atom kinds, including an urgency kind requiring expiry, with cross-client rendering semantics and a reserved signalling channel no theme may mute.
7. Ordering semantics: chronological and spatial only. This freezes the no-engagement rule into the protocol, not just the UI.
8. Federation envelope: propagation of atoms, corrections, removals and moderation actions between nodes.

### B. Spatial grammar — frozen semantics, unfrozen rendering.

9. One authoritative camera, projection, orientation, scale and selected place. No competing miniature world; no vertical-exaggeration parameter exposed to themes, ever.
10. Vertical axis = physical altitude only. Never age, urgency, popularity, reply depth, category or activity. Light never licenses flattening to 2.5D.
11. Zoom-ladder semantics: what becomes meaningful at region / district / street / exact-place scale, continuity rules between them, and deterministic aggregation derived from public atom data so all conformant clients render identical structure.
12. Query contracts: bbox+altitude+time → atoms, with deterministic pagination and dedup; and bbox+zoom → aggregates with visible provenance and freshness. Aggregates are projections, never replacements.
13. Beacon contract: every beacon resolves to an exact anchor; selection, occlusion, clustering and overlapping-altitude behaviour deterministic and accessible; customization may never detach a beacon from its anchor.
14. Board contract: reading happens in a flat screen-space surface bound to the selected place. Thread nesting and status are board semantics, never world geometry. Explicit render-boundary separation between the 3D layer and the HTML overlay; no 3D text for threads.
15. Liveness grammar: recency/urgency cues derived deterministically from timestamps — kernel-owned semantics, theme-adjustable intensity.

### C. Extension and delegation contracts.

16. Versioned theming contract stated as prohibitions first: themes may change material, colour, typography, motion, detail density; themes may not change axis meaning, aggregation truthfulness, ordering, relation semantics, urgency legibility, or add any engagement affordance.
17. Layered stability model: protocol highly stable; spatial-query and renderer contracts versioned; visual tokens free to evolve. "A frozen target" means known compatibility, not permanent appearance.
18. Render-extension boundary: extensions declare cost and capabilities and fail back to the complete baseline; arbitrary executable presentation arriving from federated nodes or atoms sits outside the trust boundary.
19. Performance-budget contract: a theme or fork is "grammar-conformant" only if it passes the named reference-device budget. This makes "cheap-to-render must not mean quiet-to-notice" testable rather than aspirational.
20. A published conformance suite — the actual frozen artifact. Artifacts hold the line when prose doesn't.
21. Accessibility equivalence: every atom reachable and legible without the 3D world (navigable text representation, screen readers, keyboard, reduced motion, non-colour status cues) without creating a second feed product.
22. Every atom resolvable as a text-first URL plus a server-rendered static preview card.

### D. Operations and governance.

23. Basemap contract: provider neutrality, attribution, projection compatibility, privacy, cache behaviour, degraded operation, and exactly what a self-hoster must supply. (The panel does not agree on whether a basemap should exist; it agrees the contract must be written either way.)
24. Media policy: whether atoms may carry attachments at all, and if so, hard caps, re-encoding limits and remote-cache expiry.
25. Kernel-level moderation tools (delist, precision-blur) plus removal propagation. Abuse cannot be delegated to pull requests.
26. Key backup and rotation; documented node budgets (town size, concurrent readers, query latency, storage growth, backup/restore, degraded behaviour).
27. RFC process and grammar versioning; visual grammar labelled provisional for 6–12 months while the wire format is not.

## 6. Three improvements to C5 that do not betray its doctrine

1. **A warmth-without-pixels pass, specified as frozen liveness grammar.** Authored empty states, human microcopy, restrained palette, deliberate easing, one procedural beacon glow, and a recency/urgency pulse computed from timestamps. Zero assets, zero downloads, negligible draw calls — and it closes the single risk C5 itself lists first ("light can read as unfinished") while restoring the only signalling channel a no-engagement system has left. This is the change that keeps C4 and C5 one product.
2. **Ship the delegation scaffolding yourselves: reference theme(s) plus a conformance suite.** Do not wait for the community to prove the theming contract. Publish the prohibition list, ship one official rich (non-default) theme that exercises every hook, and publish the visual conformance suite so forks and PRs can verify they preserved altitude, zoom semantics, urgency legibility and ordering. This converts "others will build later" from a hope into an engineered pathway, and directly answers the empirical record on delegation.
3. **Replace the single metric with a metric hierarchy, and turn the scenarios into acceptance gates.** Gates for v1: time-to-first-comprehension (a cold newcomer can state what Punkto is); urgent-post p95 under 20 s on a named mid-2019 Android over throttled 4G; a cold observer recognises the flood beacon as urgent within seconds. Ongoing: time-to-look-up, plus one ambient counter-metric — return visits with no notification of any kind, and the share of atoms read by someone who does not know the author. Forbidden: time-on-screen and anything engagement-shaped. And make "no performance budget meeting" mean a testable floor, not a ban on measurement.

## 7. Verdict

**COMBINE.**

Recommended posture: **(b) C5 merged into C4 as a strengthened phasing/shipping section** — majority position, 3 of 4, held strongly.

One document, one identity: the warm, faintly alive public world is the product; the Craigslist doctrine is how it ships. C5's three lights survive intact as the phasing chapter, amended per §5 (semantic freeze, not surface freeze) and §6 (cheap warmth in the kernel, reference theme plus conformance suite, metric hierarchy). Posture (c) is rejected unanimously: C4 as specified has no enforcement mechanism for its own conceded phasing and underestimates the federation economics that kill self-hosted networks.

Minority position, recorded and held strongly (1 of 4): posture (a) — C5 as the v1 constitution with C4 explicitly relabelled from "later phase" to "optional enrichment of a frozen grammar," on the ground that only a named constitution is binding, and that "merely a phase" is precisely how ambition re-inflates the build. The majority's own concession is that this is the merge's named risk.

## 8. Conclusion

Decision log entry — Candidate 5 review (child of Candidate 4). Verdict: COMBINE, posture (b) — Candidate 5 is merged into Candidate 4 as a strengthened phasing and shipping section, preserving one product identity (the warm, faintly alive public world) shipped under light-client, light-server, light-governance discipline. The panel was unanimous on COMBINE and unanimous in rejecting "ship C4 as specified"; a strongly-held minority preferred posture (a), C5 as a standalone v1 constitution, and that dissent is recorded rather than resolved. The merge is conditional on three amendments: the freeze is semantic, not visual (wire format, p: addressing, altitude datum plus mandatory positional uncertainty, validity/expiry, a closed relation vocabulary of reply/confirms/disputes/supersedes, a kernel urgency kind with expiry and a non-suppressible signalling channel, chronological-and-spatial-only ordering, one camera with vertical reserved for physical altitude, and an aggregate bbox+zoom query contract shipped even if implemented naively — with the visual grammar versioned and labelled provisional for 6–12 months); cheap warmth ships in v1 as frozen liveness grammar (procedural glow, recency pulse, authored empty states, human microcopy — zero assets), because in a system with no likes or counts, liveness cues are the only channel that says "people were here"; and delegation is engineered rather than hoped, via a theming contract stated as prohibitions, a kernel-shipped reference rich theme, a published conformance suite, and a reference-device performance budget, since the empirical record (truck factor of one in 57% of projects; community richness historically arriving as hard forks, not merged PRs) makes doctrine 3 non-load-bearing. Also noted for the backlog: the basemap/media policy — not rendering — is what breaks a home server first, and the panel genuinely disagrees on whether Punkto should have a basemap at all. The one condition that would prove this choice wrong: if phasing discipline demonstrably dissolves once both doctrines share one document — i.e. v1 fails to ship because C4's ambition re-inflates the light build past its reference-device budget — then C5 should have stood alone as a separate constitution (posture (a)) and this decision must be revisited; conversely, if newcomer retention in the first pilot towns fails for presentation rather than emptiness (a richer C4-shaped render over identical sparse data materially improves return visits), then C4 must be pulled forward rather than delegated. First validation test: a single-operator pilot on home hardware in one town, viewed on a named mid-2019 Android over throttled 4G in a three-atom village, gated on four numbers — (1) p95 wall clock from app-open to signed urgent atom accepted, target under 20 s, with compose independent of map load; (2) a cold observer notices the flood beacon and reads it as urgent within seconds; (3) a cold newcomer can state what Punkto is in one glance and does not call it unfinished; (4) return visits with no notification of any kind — run alongside a single-variable render comparison on identical data to isolate presentation from emptiness before the visual grammar's provisional flag is removed. Pass: proceed with the merge and the freeze list. Fail on urgency or comprehension: the cheap-warmth grammar must be redesigned before anything ships.
