# AZ Current Task

Status: **HOLD — Slice 4.5C4 deployed to test1, awaiting human relation-framing acceptance**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Current state

Pilot_1 **Slice 4.5C4 — keep the full height relation in frame** is deployed to **test1 only** from exact application SHA:

`eabb035481284b619a76db4803aeca3cf870cad5`

Commit:

`fix(pilot1): keep height relation in frame`

Served version marker:

`pilot1-slice45c4-relation-framing-2026-08-30-1`

Deployment was verified by exact SHA-256 matches for `app.js`, `ui-map.js`, `ui-create.js`, and `index.html`. Fresh browser load is clean. test1 relay/federation remains healthy with human-created atoms preserved. node1/node2 were not modified.

The remaining gate is human visual/tactile verification that height-aware framing keeps the complete physical relation visible and understandable during placement, especially around ~23 / 66 / 100 / 200 m:

- ground anchor remains visible;
- stem remains visible;
- top beacon remains visible;
- camera reframes calmly without jitter;
- lever remains associated with the visible elevated relation and does not cover it;
- Done/Cancel restore normal state.

## HOLD rule

There is no active AZ task now.

- Do not redeploy a moving `pilot-1` branch tip.
- Do not deploy/restart/modify node1 or node2.
- Do not alter test1 relay/federation topology or persistent data.
- Do not start Slice 5 until explicit ChatGPT/product instruction after human acceptance of Slice 4.5C4.
