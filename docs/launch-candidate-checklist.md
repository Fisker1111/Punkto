# Punkto 0.6 pre-alpha gate

Date: 2026-10-29. Supersedes the legacy 2026-06-22 checklist.
This is a **pre-alpha gate**, not proof of readiness or deployment authorization.
Every gate below must have reviewed evidence before a public AI invitation or
public write network is announced. Unchecked means not established here.

- [ ] Spatial-only v0.6 re-frozen; #30 integrated; independent implementation
      conformance proof reviewed and explicitly accepted by the Founder.
- [ ] `/ai` and `/nodes.json` reachable and serving the current spatial-only protocol;
      #124/#125/#127 reconciled, with GET-first reading requiring no SDK/account.
- [ ] Genuine cold-agent roundtrip archived: discover → signed anchored publish →
      static GET verification → independent peer verification → same-exact-h reply.
      A scripted harness is not independent-agent evidence; use Hermes' separate archive.
- [ ] `/submit` rate, request-size, record-count and concurrency limits documented
      and tested; storage budgets, flooding/abuse controls and disk-full behavior verified.
- [ ] Signing-key custody documented: secret reusable keys, safe backup, loss/compromise
      consequences, ephemeral-identity limits and Ed25519's lack of PQ safety.
- [ ] Consistent datastore/publication backups verified; rollback to an exact prior
      image digest tested without disagreement between atom log and publication.
- [ ] Privacy wording re-reviewed for global public spatial memory: public payloads,
      retained remote copies, sensitive-location risk and no guaranteed erasure.
- [ ] Sanitized reproducible real trace archived with exact reviewed SHA before any
      portability or persistence claim; scripted and genuine agent evidence distinguished.
- [ ] Publication lag, one-node-view limits, no presence proof and persistence through
      maintained replication/archives stated honestly; no guaranteed propagation claim.
- [ ] Founder has accepted evidence and separately authorised the public invitation.

Stage 0 local tests alone do not satisfy this gate. No shared-host seed publication,
production/staging deployment, or #32 engagement work is authorised by this file.
