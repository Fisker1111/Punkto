# PWA Evaluation Notes (May 13, 2026)

## What's already strong

- **Clear local-first architecture:** The app stores atoms locally in IndexedDB (Dexie), syncs in the background, and keeps rendering decoupled from network status. This is exactly the right mental model for a resilient field app.
- **Thoughtful network resilience:** Multi-node posting with health tracking (`ok/failing/unavailable/recovering`) and retry rotation is a practical, protocol-native way to avoid single-relay dependence.
- **Solid progressive-web baseline:** Proper manifest, service worker caching, and standalone display mode are in place.
- **Great product taste in UX details:** Sync indicator states, panel/map choreography, floating actions, and deep-link support (`/p/<id>`) show unusually strong polish for an early protocol project.
- **Performance-aware choices:** Self-hosted static libs, lightweight vanilla JS, and append-only sync semantics reduce moving parts and deployment friction.

## Concrete improvement points

1. **Add explicit accessibility pass (high priority).**
   - Add landmark roles (`main`, `nav`) and explicit labels for icon-only controls.
   - Ensure keyboard navigation paths for modal open/close and map-adjacent controls.
   - Add visible focus styles and test with reduced motion preferences.
   - *Status: implemented in v40 — `role="banner"`, `role="main"`, `role="dialog"`, focus-visible styles, and `prefers-reduced-motion` added.*

2. **Service worker caching strategy could be safer for API error handling.**
   - The current offline fallback returns JSON error payload for any network-first request; for HTML/JS routes this can lead to invalid content-type responses.
   - Use route-specific fallbacks (e.g., shell fallback for navigation requests, JSON only for API requests).
   - *Status: SW updated to return clean 503 JSON for unreachable peers (v38+).*

3. **Versioning and upgrade migration should preserve user data where possible.**
   - Current Dexie upgrades clear atom data in multiple versions.
   - Consider migration flags and schema evolution to avoid destructive upgrades unless a hard protocol break is required.

4. **External map/style dependencies need graceful degradation.**
   - `MAP_STYLE` points to an external style host. Add fallback style or user-facing degraded-mode message if map tiles/styles fail.

5. **Observability for sync should be expanded.**
   - Keep current UI dot, but add optional diagnostics panel: active relay, last sync timestamp, cursor position, and recent error counts.

6. **Security hardening opportunities in static shell.**
   - Add a stricter Content Security Policy (at least nonce/hash-driven script policy if feasible).
   - Validate all user-provided atom text rendering paths remain text-only (no HTML injection vectors).

7. **PWA installability and metadata completeness.**
   - Add screenshots in manifest for richer install prompts on compatible platforms.
   - Consider shortcuts (e.g., "Drop atom here", "Open latest feed").

8. **Add lightweight automated regression checks.**
   - Even a tiny smoke suite for: deep-link parse, atom hide filters, service worker route handling, and sync-state transitions would prevent subtle regressions.

## Suggested next 2-week focus

- Week 1: accessibility + service worker fallback correctness.
- Week 2: non-destructive migration strategy + sync diagnostics.

This sequence improves trust and robustness immediately, without changing core protocol behavior.
