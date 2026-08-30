# AZ Current Task

Status: **HOLD — stable-placement build deployed to test1; human testing found draft-render regression**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`
PR: `#110`
Owner: **AZ (deployment / operations)**

## Current state

The reviewed application SHA below was deployed to test1:

`0ed108d9e92d147a40ff1f9bb553d042ad72ecbb`

Version marker:

`pilot1-slice45c4-stable-placement-2026-08-30-2`

Human verification confirms the build is running, but the world-space yellow placement atom is still not visible. The regression is now being handled by Codex by restoring the last human-accepted Slice 4.5B2 height-placement rendering/interaction path as the reference.

## HOLD rule

There is no active AZ deployment task now.

- Do not redeploy a moving `pilot-1` branch tip.
- Do not modify/restart node1 or node2.
- Preserve test1 relay/federation topology and persistent data.
- Do not start Slice 5 until explicit ChatGPT/product instruction.
- Wait for an exact reviewed application SHA after the B2-reference restoration fix.
