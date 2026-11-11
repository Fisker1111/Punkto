# Punkto launch packet — discoverability, Show HN plan and a <= $20 acquisition test

## How to read this packet

This is a decision packet, not a launch: no post was published, no account was created, no money was spent and no card was bound. Every publish or spend action requires founder review of the exact venue, copy and cost. The Hermes-side MCP checks described here are **operator QA, not customers**. Evidence comes from the specification's dated verified facts, not new network requests during document preparation.

## Gate: what must be true before anything is published or spent

Gate assessment checked on 2026-11-11, using the 2026-11-10 live/browser evidence and 2026-11-11 issue statuses:

| Hard precondition | Current status | Evidence / next action |
|---|---|---|
| PWA first-run usable without signup | MET | Apex PWA serves; fresh browser has no signup/login form, no console errors and a populated NEARBY TEXT feed; `/ai` reads require no account. |
| MCP M9 customer-facing readiness, CEO-OS #61 | NOT MET | Issue OPEN, labels `status:review`, `worker:hermes`, `priority:p1`; moved from `status:in-progress` on 2026-11-10 to `status:review` on 2026-11-11, not closed. Founder must confirm readiness completion. |
| DNS www cutover, CEO-OS #58 | NO-GO | Issue OPEN, labels `status:review`, `worker:hermes`, `priority:p1`; `www.punkto.xyz` does not resolve. Never use it as a landing destination. |
| Founder approval of exact venue, copy and cost | Pending | This document is a proposal, not approval. |

Therefore **no promotional submission, no publication and no spend may happen yet**. CEO-OS #59, Punkti v0.6 deploy, was CLOSED with `status:done` when checked on 2026-11-11; that does not satisfy the other gates.

Readiness check the founder can run in 10 minutes, after resolving the open gates:

1. Open [the apex PWA](https://punkto.xyz/) in a private window. Confirm no signup barrier, no console errors, a readable feed and Text / Map / + / Settings navigation. The baseline visible atoms were all internal operator QA material, not organic outside activity.
2. Open [the AI entrance](https://punkto.xyz/ai) without an account and inspect the published Null Island conversation.
3. Run the `initialize` curl below. Expect HTTP 200, SSE-framed JSON-RPC over Streamable HTTP, protocol `2025-06-18`, `serverInfo` name `punkto-mcp`, version `0.1.0`, and `tools.listChanged` capability.
4. Run `tools/list`; confirm exactly `read_place`, `get_record`, `discover_places`, all read-only. Repeat in a fresh MCP client session and record the outcome as QA.
5. Check the documented helper URL below. `https://punkto.xyz/punkti/punkto-reply.mjs` returned HTTP 200 on 2026-11-10. The bare `https://punkto.xyz/punkto-reply.mjs` returned HTTP 404; check and advertise only the `/punkti/` path.

```bash
curl -i -X POST https://punkto.xyz/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"founder-readiness-check","version":"1.0.0"}}}'
curl -i -X POST https://punkto.xyz/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
curl -fsS -o /dev/null -w '%{http_code}\n' https://punkto.xyz/punkti/punkto-reply.mjs
```

These are future manual checks. GET `/mcp` returning 405 is expected for the POST-only endpoint.

## Channel A — AI-agent and developer discoverability (prefer $0)

Execute only after the gate and founder approval. Use [MCP_REGISTRY.md](MCP_REGISTRY.md) and the exact [server.json](../../server.json) payload.

| Order / action | Cost | Current status | Founder action / click |
|---|---|---|---|
| 1. Official MCP Registry | $0 planned; fee not specified in verified facts, confirm before action | No Punkto or Punkti listing, both searches returned 0 on 2026-11-10; payload is an unpublished draft | Open the registration guide, choose domain proof, perform manual login and publish, then inspect the exact-name search result. This is a CLI publication, not a fabricated dashboard button. |
| 2. Glama remote connector | Free $0; optional paid boost approximately $49/month is rejected | Checked 2026-11-11: no Punkto connector or server page; proposed domain and GitHub connector URLs both 404; healthy baseline 0 | Open Glama, choose remote HTTPS connector submission, enter `https://punkto.xyz/mcp`, and follow its claim/health-check flow. Separately approve hosting `/.well-known/glama.json` with the schema and maintainer email in the registry guide. |
| 3. mcpservers.org curated technical directory | Free $0, review within 2 weeks; $39 one-time review within 24 hours is **not recommended by default** | No submission made by this task; existing listing status unverified | Open the submission form, choose the free plan, enter the official registry name in “Official MCP Registry Name (optional)” and select “This server supports remote connections”. Review before submitting. |
| 4. awesome-mcp-servers GitHub PR, follow-on | $0 planned; any fee unverified | No PR made by this task; existing listing status unverified; Glama badge prerequisite not met | Once the Glama badge exists, open the relevant curated repository, follow its contribution rules, and create a reviewed PR. For awesome-remote-mcp-servers, supply a live Glama connector badge, star the repo and pass its live `initialize` CI. |

Glama's registry import/re-publication path is separate from its health-checked remote connector path; this endpoint is a remote connector, not an installable server. Exact UI button labels and any unspecified fees are to be confirmed by the operator, not invented here.

Registry/directory listing is **machine access via a catalogue**. No directory guarantees that any model or agent will notice, prefer or use the server. A listing is not evidence of demand and a registration is not a customer.

There will be no fake reviews, bots, automated account creation or manufactured endorsements. All submissions remain founder-reviewed manual actions.

## Channel B — human developer launch ($0)

This is a Show HN plan, not a submission or ready-to-post generated copy. The try-without-signup precondition is met by [the PWA](https://punkto.xyz/) and [the AI entrance](https://punkto.xyz/ai): on 2026-11-10 the fresh PWA session had no signup/login form and a populated feed, while `/ai` was readable via plain HTTP GET. Every visible first-run atom was internal operator QA. The product is tryable, but that feed is operator-labelled and is not evidence of organic traction. The submission must lead to the actual tryable work; a signup wall, waitlist, landing page, blog post, newsletter or reading list does not qualify for Show HN.

HN rules in the supplied verified facts require personal work by the poster and availability to discuss it: “Please make it easy for users to try your thing out, ideally without barriers such as signups or emails.” They also say “Please don't put generated text in HN posts” and “Please don't ask friends to upvote or comment”. The founder must be present to answer questions; no link farming, automated posting or community spam. Routine new features generally are not substantive enough; a major overhaul may qualify. Eligibility of the founder's proposed submission is for the founder to confirm.

Hermes supplies facts and an outline only. **The founder writes and posts the Show HN title and first comment in their own words**, rather than copying this generated packet. If the founder is not personally available in the thread for the first few hours, do not submit yet.

Factual outline for the founder's own writing:

- What it is: **Punkti = open, universal, signed spatial protocol (network stays interoperable). Punkto = one commercial service/provider on that network (SMTP/Proton-like model).** Approved messages: **Addressability · Distribution · Persistence** and **Leave a mark**.
- Show the real Null Island conversation published on `/ai`, values read 2026-11-10. Address `h=s00000000000_0` is 0°,0°, height 0 m, an explicit symbolic WGS84 ellipsoidal choice, not ground elevation. The address is not reserved and proves neither presence nor ownership.
- Root MID: `punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed`. Root SHA-256: `2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d`. [Root binary record](https://punkto.xyz/publication/records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d).
- Reply text: “Hello from a new AI”. Reply MID: `punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854`. Reply SHA-256: `0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b`. [Reply binary record](https://punkto.xyz/publication/records/0c/0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b). This is a verifiable example, not a claim of an unaffiliated customer.
- Reading uses plain HTTP GET, with no account, Node, npm or SDK required. Raw records are binary, not JSON or text; decode client-side and verify SHA-256, canonical MID and Ed25519 signature. The product warns that “a server saying VALID is not evidence”. Hashes alone do not prove authenticity.
- Publishing is optional: after downloading the helper, the reply invocation is one command. Only the optional helper requires Node.js 20.19+/22+, never reading. It does not make MCP writable; MCP remains read-only convenience and plain HTTP GET via `/ai` remains the universal fallback, never redirected or changed.
- Persistence means continued replication by independent operators, not a promise. Do not claim immutable omnipresence or guaranteed permanence.

Read command shown on `/ai`:

```bash
curl -fsS https://punkto.xyz/publication/records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d -o null-island.bin
```

Optional helper download, followed by the one-command reply invocation:

```bash
curl -fsS https://punkto.xyz/punkti/punkto-reply.mjs -o punkto-reply.mjs
node punkto-reply.mjs reply punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed "your text" --origin https://punkto.xyz
```

These are illustrative future actions, not executed here. The product's own stated limits on `/ai`, read 2026-11-10:

- “The default identity is an ephemeral Ed25519 key in memory”
- “Ed25519 is not post-quantum.”
- “Atoms are public, unencrypted and possibly independently archived.”
- “Location does not prove presence; a key signature does not prove the actor or statement's truth.”
- “Submission acceptance ≠ publication visibility ≠ preservation. Publication can lag; hosting may limit submissions.”
- “The receipt distinguishes accepted, visible and verified; replication is not-measured.”
- “Independent custody is not guaranteed; nothing is guaranteed to survive forever.”

Proposed 30-second demo, with speaking cues for the founder to express in their own words:

| Time | Show, in order | Point to explain |
|---|---|---|
| 0–5 seconds | Open `/ai` without login | Reading is available without an account. |
| 5–15 seconds | Null Island root and reply, coordinate, MID and SHA-256 | These are published records at a symbolic coordinate; neither presence nor organic traction is established. |
| 15–25 seconds | Plain GET command and a prepared client-side decode/verification result, only if actually verified | Bytes are binary; check hash, canonical MID and signature. Do not fabricate a successful verification or pretend it completes live in this interval. |
| 25–30 seconds | Optional reply command and stated limits | Publishing is optional; public records and continued replication do not guarantee preservation. |

“Why does this exist?” is a question for the founder to answer in their own words, not a supplied HN paragraph. The factual basis is addressable signed spatial records, an open interoperable protocol, Punkto as one commercial provider, and reading through ordinary HTTP independently of the MCP convenience layer. The founder can explain which real problem motivated their personal work and why those properties matter, while acknowledging that independent custody and persistence are not guaranteed; this packet provides no evidence of customer demand or of a personal origin story.

Alternative: a genuinely helpful technical thread in a self-hosting, preservation or AI-infrastructure community that permits it. No forum is declared approved. The founder checks its local self-promotion rules, answers other people's questions first, and posts no link unless the rules allow it.

## Channel C — paid experiment (hard ceiling $20 all-in)

Proposal awaiting approval. Compare exactly two advertising paths; recommend **Reddit Ads Standard**, because community targeting supports a deliberately bounded developer audience.

| Path | Published prices/minimums and billing | Limits and fit |
|---|---|---|
| Reddit Ads Standard campaign, Traffic objective | Get Started has a $5 daily floor, but this proposal uses Standard with an ad-group lifetime budget and campaign spend cap. Daily ad-group budgets may overspend by up to 20% in live auctions. Charges exclude taxes; taxes, levies and FX fees fall to the advertiser. No fixed Standard Traffic unit price or minimum lifetime budget is supplied in the verified facts; operator to confirm. | “The campaign spend cap is the maximum amount your campaign can spend over its lifetime. Campaigns are never billed more than this amount.” Lifetime ad-group budgets cover fixed start/end dates; budget type cannot be changed after saving. Review normally takes up to 48 business hours and can take longer. |
| X Ads | No minimum spend; daily maximum plus optional campaign total budget. Engagements objective is billed per engagement: “An engagement includes all clicks on your posts, including reposts, replies, likes, poll votes, and hashtag clicks.” Website traffic is billed on impressions (CPM) and link clicks (CPC), optimised towards link clicks and site visits, depending on bid setup. | Daily-budget guarantee: “we will never go over this amount.” Overall-budget rule: “When your overall budget is reached, your campaign will stop serving until you increase the budget.” Bid guarantee: “you will never be charged more than your bid and advertisers are often charged less.” The bid is a per-result ceiling, not a fixed price or a guarantee of visits. Auction pricing is not a flat per-click tariff. |

Reddit's own guidance recommends $50/day+ per ad group with a 2–4 week learning phase, and approximately $100/day in marketing guidance. A <= $20 test is far below that scale: report it as a **smoke test, not an optimisation experiment**. X's maximum-bid wording is retained as a bid ceiling, without asserting a price that the verified facts do not provide.

Reject newsletter sponsorship/listing spend for this budget: published October–November 2026 prices put the median main sponsorship at $350 per issue (420 priced newsletters, read 2026-11-04), middle half $200–$750, Dev Leader Weekly $300 and JavaScript Weekly $3,680. These are one-issue flat fees above $20, so a newsletter slot is not feasible. Paid directory expedites of $29 or $39 and Glama's approximately $49/month boost also exceed the ceiling; free listings stay in Channel A.

Recommended setup, founder-approved **before anything is created**:

- One Reddit Ads **Standard** campaign, objective **Traffic**, one ad group, one ad.
- Ad-group **lifetime budget $16**, with fixed start and end dates exactly 3 days apart; select lifetime type before saving.
- Explicit **campaign spend cap $16**, the hard lifetime ad-spend ceiling. No additional ad groups and no second creative.
- The cap leaves $4 of the $20 all-in ceiling for VAT/levies/FX. The daily-budget 20% overshoot rule is avoided by selecting the lifetime budget type, and the campaign cap remains the hard ad-spend ceiling. The $4 reserve is not evidence that actual fees fit: the operator must confirm taxes, fees, currency conversion and that a $16 lifetime setup is accepted before creation. If total charges cannot be kept at or below $20, do not start this proposal; return for a revised founder decision.
- Community/subreddit targeting **only**: `r/selfhosted`, `r/LocalLLaMA`, `r/programming`, `r/MCP`, `r/opensource`. No interest categories, broad targeting, lookalikes or custom audience uploads. Confirm actual availability in the UI; subreddit owners can opt out of ads, so delivery may fall short of budget and underspend alone is not failure.
- Submit for ad review **at least 48 hours before** the planned start; allow for up to 48 business hours or longer. The 3-day observation window cannot start on campaign-creation day. Changes to copy, destination URL, budget or creative send the ad back for review; reschedule rather than assuming approval.
- Do not raise the $16 campaign spend cap without a new founder decision. End on the fixed end date even if the cap is not exhausted, and record actual billed cost rather than treating the cap as spend.

One creative concept, a copy brief for founder editing, not an approved ad:

| Element | Proposed brief |
|---|---|
| Headline options | “Leave a mark” or “Addressability · Distribution · Persistence”. Choose one for the single ad. |
| One body line | “Read signed spatial records through plain HTTP; explore the Null Island conversation.” |
| Visual | One static image showing a marked coordinate on a dark background; no stock photos, fake UI or claims of permanence. No image is created in this task. |
| Destination | `https://punkto.xyz/ai`, not the map PWA root and never the unresolved www host. |
| Tagged destination | `https://punkto.xyz/ai?utm_source=reddit&utm_medium=paid&utm_campaign=launch62`; keep the destination under Reddit's 268-character limit and the display URL matched to the landing page. |
| Wording constraints | No “permanent”, “immutable”, “guaranteed”, invented user counts, “the first” or “encrypted”. Persistence must not imply guaranteed survival. |

Landing-destination readiness gap, verified 2026-11-10: Reddit reviews the landing page. Its **editorial requirements are hard rules**: matching display and landing URL, advertised product available on the landing page, no spam or non-functioning links, and compliance with Reddit Rules and Advertising Policy. The supplied verification says `/ai` satisfies those requirements; it is functional, offers the product and links to the GitHub repository. This is not a promise of ad approval.

Reddit's additional **landing-page tips are recommendations**, including an SSL certificate, no personal-information gate and clear links to Terms of Service, Privacy Policy and Contact/About. `https://punkto.xyz/privacy.html` exists and states no account required and no tracking; it also describes append-only atom storage. There is no Terms page (`/terms`, `/tos`: 404), no About or Contact page (`/about`, `/contact`: 404), and `/ai` links to none of those pages, including privacy. Recommend adding Terms and Contact pages and linking them and privacy from the destination before spending, to lower review-failure risk. Those site changes are outside this task. Alternatively the founder may explicitly accept that review risk; silence is not acceptance. This decision is an open dashboard item.

**No spend until the Gate is met and the founder has approved the exact venue, exact creative and exact $16 campaign cap in writing**, with an all-in cost check at or below $20.

## Measurement and honest evaluation

Use supportable aggregate observations, not invasive identification:

| Measure | Source and access | Method and limit |
|---|---|---|
| Impressions, link clicks and spend billed | Operator opens Reddit Ads Manager | Record platform results and campaign destination tag. The exact tagged-link reporting/breakdown available in the account is unverified; confirm before relying on it. Impressions are not customers. |
| Tagged landing visits | Operator/ops inspects node1/node2 Caddy access logs | Use `?utm_source=reddit&utm_medium=paid&utm_campaign=launch62`. The repository's site blocks use `output stderr`, `format console`, `level INFO`; console access logs contain the request URI. Query-string inclusion is **not verified**: do a 5-minute operator check before launch using a test tag, then exclude that QA request. Count requests, not unique humans. If tags are missing, report unavailable instead of inventing visits. |
| Aggregate MCP requests | Founder/ops opens Cloudflare Worker analytics for `punkto-mcp` | The adapter is that Worker (`workers_dev: true`). Hermes did not and cannot read its analytics. Aggregate counts do not establish distinct users, handshakes or unaffiliated clients; report those separately only with voluntary external evidence. No user identifiers. |
| Genuine outside interest | Manual review of voluntary GitHub issues, HN comments, email replies and external operators' own reports | Count unaffiliated operators who independently fetch, verify or reply, and substantive questions/comments. Do not assume every request is a person or every record is unaffiliated. |
| Conversion | Published records themselves | Count only a voluntarily published real signed mark, with independent verification and voluntary evidence of unaffiliated origin; uncertain affiliation stays unknown. Acceptance receipts alone are not publication. |
| Total cost actually billed | Platform bill plus applicable taxes, levies and FX | Record actual all-in amount; pending settlement stays pending, not $0 or the budget cap. |

No fake AI visitors, automated account creation, manufactured posts or counted QA sessions. Operator QA, including the Hermes MCP checks, is reported separately from outside interest. No personal data is collected beyond what an ad platform and server access log already record; do not add identifiers or attempt to identify anonymous readers. A registration or listing is not a customer.

Use a **3-day observation window after any public promotion**, with the paid test's dates aligned to approved delivery rather than account creation or ad review. Record each channel's window separately. No autonomous background follow-up is promised: there is no scheduled system in place, and the day-3 review is a manual operator action. If billing has not settled on day 3, report that and reconcile manually later.

## Success dashboard

Baselines below are the supplied dated checks, not new measurements. Targets are proposed decision thresholds, not forecasts or invented observed metrics; the founder approves them with the test.

| Metric | Source | Baseline | 3-day target | How measured | Honest interpretation |
|---|---|---|---|---|---|
| Registry listing published | Exact-name official registry search | 0, checked 2026-11-10 | 1 after gate and founder publication | Inspect exact `server.name`, version and remote | A listing with zero traffic is a metadata success and a demand failure, and must be reported as such. |
| Glama connector healthy | Glama connector page and health check | 0, checked 2026-11-11: no Punkto connector/server page; both candidate connector URLs 404 | 1, subject to processing | Founder checks claimed live connector and health result | Health means endpoint availability, not usage; registry import alone is not a healthy connector. |
| Directory listings live | mcpservers.org / curated-list pages | Unverified; no submission by this task | 1 free submission; live listing tracked, no 3-day approval promise | Founder records actual live URL or pending review | Free mcpservers.org review can take 2 weeks; pending is not rejection or a customer. |
| Tagged landing visits | Caddy access logs | Unverified; query logging not yet confirmed | Measurement check passes, then at least 1 non-QA tagged request | Inspect query retention; count tagged requests excluding known QA | Requests are not unique people; bots/unknown traffic are not demand. Missing instrumentation is not zero traffic. |
| MCP handshakes from unaffiliated clients | Voluntary external-client verification; Worker aggregate counts as context | Unverified; Hermes checks are QA | At least 1 externally evidenced handshake | Manual external report of initialize result; keep aggregate requests separate | QA excluded; aggregate Worker counts alone cannot prove affiliation or handshakes. |
| Voluntary signed marks from unaffiliated operators | Published records and voluntary external evidence | Unverified; visible first-run feed was operator QA | At least 1 verified published mark | Fetch/decode, verify SHA-256, canonical MID and Ed25519 signature; exclude QA | One unaffiliated verified reply is a stronger signal than 1,000 impressions; signature alone proves neither actor nor truth. |
| Genuine outside comments/questions | Voluntary GitHub issues, HN comments, email replies | Unverified | At least 1 substantive unaffiliated question/comment | Manual count, excluding operator QA and solicited engagement | A real question is interest, not a purchase or guaranteed retention. |
| Total spend billed | Ad bill, taxes, levies and FX | $0 spent by this task; unrelated historical spend unverified | <= $16 ad spend and <= $20 all-in; $0 until gate | Actual billed total, with unsettled fees marked pending | Cap is not actual spend; underspend alone is not failure. |
| Landing-destination readiness decision | Founder review of `/ai` and missing policy/contact links | OPEN: no Terms/Contact/About pages and no privacy link from `/ai` | Explicit fix-or-accept-risk decision before spend | Founder records decision; any site work happens separately | Tips are not hard editorial rules, but ignoring the gap is not approval. |

**Stop:** keep everything blocked until the gate passes; once running, stop at the fixed end date or cap, or earlier if the destination fails or the all-in ceiling cannot be kept. No second ad or ad group.

**Continue:** if the 3-day window produces at least one unaffiliated verified mark, externally evidenced MCP handshake or substantive outside question, the founder may approve one more separately bounded test with an explicit cost ceiling. This is permission to consider a new test, not automatic renewal.

**Stop-and-rethink:** if measured non-QA visits arrive but yield none of those outside signals, the channel/message has not shown useful demand; do not repeat paid spend unchanged. If listings yield no traffic, report metadata success and demand failure. If delivery is absent or measurement unavailable, call the result inconclusive and resolve that specific problem before considering another test; do not blame underspend alone.

## What Hermes did not do

- No registry account and no credential.
- No publication and no directory submission.
- No paid account, card or campaign.
- No email, post, forum thread or Show HN submission.
- No fake review or bot and no upvote solicitation.
- No change to live product code and no deployment.

In the prior verification described by the specification, the only live interactions were read-only GET/POST verification requests against `https://punkto.xyz` and `https://punkto.xyz/mcp`; they were not product-state changes. This document-writing task made no network calls.

**Notes and open items**

- The gate status is assessed on 2026-11-11 using dated 2026-11-10 browser/endpoint checks; this packet does not claim a fresh browser test. OPEN/review is not readiness completion.
- Channel A uses the required order: registry, Glama connector, free mcpservers.org, then curated PR after the badge. Registry/PR costs are $0 planning assumptions where verified facts give no price; unspecified existing directory listings, UI labels and review timing remain operator checks.
- HN material is an outline and demo cues, not a generated post; the founder supplies their own words and motivation. The optional reply is one invocation after helper download, with Node needed only for that helper.
- X billing follows the verified objective-dependent CPM/CPC and engagement wording; the bid guarantee is a per-result ceiling, not a flat price. Reddit Standard lifetime minimum and unit pricing are unverified; only the Get Started $5 daily minimum is established.
- The $16 ad cap leaves a proposed $4 reserve, not a guarantee about taxes/FX. Confirm all-in fees and lifetime-budget availability before creation. Review must precede the 3-day run by at least 48 hours, allowing longer for business-hour review or changes.
- Missing Terms/Contact pages and privacy links are a separate site decision; landing-page tips are distinguished from hard editorial requirements. The founder must explicitly choose repair or acceptance of review risk before spend.
- Dashboard numeric targets are proposed thresholds, not factual forecasts. Unknown baselines remain unknown; directory timing may exceed 3 days. Tagged-query logging and platform tag breakdown need operator checks, and aggregate Worker analytics cannot establish unaffiliated handshakes.
- Prior read-only verification is called live interaction rather than “live changes” to avoid implying a deployment or state mutation. No network verification was performed for this writing task; day-3 review remains manual.
