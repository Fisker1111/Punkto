# AZ Current Task

Status: **HOLD — Slice 4.5 accepted; Slice 5 implementation is owned by Codex**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Current state

The deck-overlay visibility fix is deployed to **test1 only** from exact application SHA:

`71053f1743c9982f0ce1420ae99beedc0bdb440a`

Commit:

`fix(pilot1): keep deck overlay visible during height placement`

Human verification confirms the height-placement world object is visible again: yellow draft atom, ground relation, and vertical stem are readable with the right-side lever. The Slice 4.5 placement issue is therefore **accepted and closed for now**.

The accepted creation interaction remains:

> **Aim → `+` locks x/y → choose physical height → Done → Write → Publish.**

Do not redesign or reopen that mechanism during operations work unless a new blocking defect is explicitly reported.

## Next phase

**Slice 5 — Finish Punkto** is now an application/product implementation task and belongs to Codex first.

AZ has no active deployment task until ChatGPT reviews the completed Slice 5 application SHA and Pilot CI is green.

## HOLD rule

- Do not deploy the moving `pilot-1` branch tip.
- Do not edit Punkto application/product code.
- Do not modify/restart/deploy node1 or node2.
- Preserve test1 relay/federation topology, node identity, persistent volume, and human-created atoms.
- Do not begin production/main cutover. That is Slice 6 and requires explicit authorization.
- Wait for an exact reviewed Slice 5 application SHA from ChatGPT.
