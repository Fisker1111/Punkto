# NairobiDot L3 × reference Mesh interoperability

Python 3.14.7 (CPython); loopback HTTP only.
Implementation identity: SHA-256 of every source file is recorded in `interop_report.json`.
Reference source manifest SHA-256: `9aeb65501095c7756980e39c095ad0ecb838cdcddac569d82ed48b454492e6ee`.
Clean-room source manifest SHA-256: `6c7601e1fd3e7b678248389527789c165ae97b2ffb072329c8223457194035c9`.
Convergence arrangement: two clean-room nodes and one reference.

| Test | Result | Evidence |
|---|---|---|
| connect_both_initiators | PASS | 48 recorded comparisons; Each implementation initiates full reciprocal connect over mixed atoms. |
| convergence_orders_and_subsets | PASS | 50 recorded comparisons; Two clean-room plus one reference converge after two fair sync rounds. |
| decode_parity | PASS | 103 recorded comparisons; Both standalone adapters decode the other implementation's records. |
| disconnect_rejoin_cursor_catchup | PASS | 60 recorded comparisons; Both initiators survive refused proxy, reuse cursor, pull only new records. |
| http_duplicate_key_divergence | PASS (documented divergence) | 23 recorded comparisons; Duplicate HTTP envelope keys are accepted only by the reference. |
| no_reference_imports | PASS | 30 recorded comparisons; Static scan and isolated import prove clean-room source independence. |
| push_both_directions | PASS | 33 recorded comparisons; Both HTTP push directions admit VALID and return identical R/digests. |
| rejection_consistency | PASS | 142 recorded comparisons; Carrier/data-level rejection agrees; valid records later win. |
| request_validation_divergences | PASS (documented divergence) | 45 recorded comparisons; Pin four revised agreements and two out-of-scope request differences. |
| spatial_range_selection | PASS | 74 recorded comparisons; Padded lower-edge XY bounds filter push admission and peer PULL. |
| unknown_l4_byte_preservation | PASS | 85 recorded comparisons; Unicode, JSON-looking text, unknown refs/ext/alg survive exact transfer. |
| vector_parity | PASS | 67 recorded comparisons; Six deterministic vectors compare all canonical and framed bytes. |
| xy_z_profile_vectors | PASS | 3 recorded comparisons; Every deterministic XY_Z vector runs on both process-isolated codecs. |
| xy_z_selection | PASS | 66 recorded comparisons; Same XY with separate decimal Z agrees at exact height boundaries. |

Totals: 14 PASS, 0 FAIL.

| Vector | MID | Address |
|---|---|---|
| unanchored | 87bd4380e5580124d46e4a4a43192d8afa3b5a0855ae90e0b564d713e10abfa8 | punkti/0.6:87bd4380e5580124d46e4a4a43192d8afa3b5a0855ae90e0b564d713e10abfa8 |
| XY | 9d1db8cd4d6b989a48b75d783cea08b4f4a294b0c6d75627df711b00d729de47 | punkti/0.6:9d1db8cd4d6b989a48b75d783cea08b4f4a294b0c6d75627df711b00d729de47 |
| XYZ | 7936aa912dbf6dc37937945c55cb62140339cea74f376885118bab94eba49c1a | punkti/0.6:7936aa912dbf6dc37937945c55cb62140339cea74f376885118bab94eba49c1a |
| refs-order-duplicates | cbb1e21bf0de33e73d9933e3fccc1961d115fd356ca43e97e31b7e40ce9c32ae | punkti/0.6:cbb1e21bf0de33e73d9933e3fccc1961d115fd356ca43e97e31b7e40ce9c32ae |
| unicode-ext | 0cdd9f5dd56846bcb05485116ad1cbdf46a97c90c61d6927691bcb38dcad8975 | punkti/0.6:0cdd9f5dd56846bcb05485116ad1cbdf46a97c90c61d6927691bcb38dcad8975 |
| unknown-alg | 1131ff3d12b7f9e3e93e61563c53a703b3129795b986fa748d13813f373eae48 | punkti/0.6:1131ff3d12b7f9e3e93e61563c53a703b3129795b986fa748d13813f373eae48 |

## Divergences

- http_duplicate_key_divergence: HTTP envelope duplicate JSON keys: reference keeps the last records key and admits the record; clean-room rejects with HTTP 400 and stores nothing.
  - Reference: `{"addresses": ["punkti/0.6:3f9b50723d7f6de84f05b8d78d2f28c98c795d0cea43168ec3e9a08022cd223c"], "candidates": [], "http_status": 200, "log": [{"address": "punkti/0.6:3f9b50723d7f6de84f05b8d78d2f28c98c795d0cea43168ec3e9a08022cd223c", "seq": 1, "sha256": "b861219f542e1c83bc2218af9bae26b4e0d43615f4bc1faf8cc053bdff7d2857"}], "response": {"results": [{"admitted": true, "state": "VALID"}]}}`.
  - Clean-room: `{"addresses": [], "candidates": [], "http_status": 400, "log": [], "response": {"kind": "request", "reason": "json"}}`.
- request_validation_divergences: Two remaining out-of-scope request-validation divergences: unknown query member and empty push batch. Revised interval bounds and wrong-address tiers agree.
  - GET /pull query {mode:'spatial',extra:1}: reference HTTP 200, member ignored; clean-room HTTP 400, kind='request', reason='query-fields'.
  - POST /push {records:[]}: reference HTTP 400, error 'push batch size'; clean-room HTTP 200, {results:[]}.
  - Reference: `{"empty push batch": {"http_status": 400, "response": {"error": "push batch size"}}, "equal XY bounds": {"http_status": 400, "response": {"error": "equal or reversed bounds: xy"}}, "equal elevation": {"http_status": 400, "response": {"error": "equal or reversed bounds: z"}}, "reversed elevation": {"http_status": 400, "response": {"error": "equal or reversed bounds: z"}}, "unknown query member": {"http_status": 200, "response": {"cursor": {"after": 0, "ceiling": 0, "epoch": "<epoch>", "scope": "07eea3d4eef7a2c6dd24f0385438ddaddbdc96e7780f1211285449eeb4e2b399"}, "end": true, "records": []}}, "wrong address for VALID record": {"http_status": 400, "response": {"error": "address mismatch"}}}`.
  - Clean-room: `{"empty push batch": {"http_status": 200, "response": {"results": []}}, "equal XY bounds": {"http_status": 400, "response": {"kind": "request", "reason": "equal or reversed bounds"}}, "equal elevation": {"http_status": 400, "response": {"kind": "request", "reason": "equal or reversed bounds"}}, "reversed elevation": {"http_status": 400, "response": {"kind": "request", "reason": "equal or reversed bounds"}}, "unknown query member": {"http_status": 400, "response": {"kind": "request", "reason": "query-fields"}}, "wrong address for VALID record": {"http_status": 400, "response": {"kind": "request", "reason": "address-mismatch"}}}`.

Exact compared values and raw HTTP evidence are in `interop_report.json`.
