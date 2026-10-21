# NairobiDot L3 × reference Mesh interoperability

Python 3.14.7 (CPython); loopback HTTP only.
Implementation identity: SHA-256 of every source file is recorded in `interop_report.json`.
Reference source manifest SHA-256: `3967410ebc8ead848cd832f29d47bd1069b6b3a0143f4a63ca5f9f60a852a1dd`.
Clean-room source manifest SHA-256: `caf9d0c4b08b1904a100a1596fe6311895f2d7b20d0a1d6e39241b84676371b6`.
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
| request_validation_divergences | PASS (documented divergence) | 44 recorded comparisons; Pin six request-validation differences without requiring parity. |
| spatial_range_selection | PASS | 74 recorded comparisons; Literal half-open h bounds filter push admission and peer PULL. |
| unknown_l4_byte_preservation | PASS | 85 recorded comparisons; Unicode, JSON-looking text, unknown refs/ext/alg survive exact transfer. |
| vector_parity | PASS | 67 recorded comparisons; Six deterministic vectors compare all canonical and framed bytes. |
| xy_z_selection | PASS | 66 recorded comparisons; Fixed XY bits with varying Z agree at exact altitude boundaries. |

Totals: 13 PASS, 0 FAIL.

| Vector | MID | Address |
|---|---|---|
| unanchored | 87bd4380e5580124d46e4a4a43192d8afa3b5a0855ae90e0b564d713e10abfa8 | punkti/0.6:87bd4380e5580124d46e4a4a43192d8afa3b5a0855ae90e0b564d713e10abfa8 |
| XY | 7a1e1d6e9b4b1a0637bcacd771758619555f419c881797e1730d59e01f7f6301 | punkti/0.6:7a1e1d6e9b4b1a0637bcacd771758619555f419c881797e1730d59e01f7f6301 |
| XYZ | f7d9dafe4d2bbeaafe7367db1d9b40762760abae0a096ac624a60e9e27579fca | punkti/0.6:f7d9dafe4d2bbeaafe7367db1d9b40762760abae0a096ac624a60e9e27579fca |
| refs-order-duplicates | 37016dd1af177b43a5f5a1991603dc9438bb8f149b729020b50d79e35d04049d | punkti/0.6:37016dd1af177b43a5f5a1991603dc9438bb8f149b729020b50d79e35d04049d |
| unicode-ext | 8d72c892016d6db3e4017383bddc7a0acb9314e72ca69dab5c62fbc3294293cd | punkti/0.6:8d72c892016d6db3e4017383bddc7a0acb9314e72ca69dab5c62fbc3294293cd |
| unknown-alg | 2dc0696a81f0afaf69dddc2da34cc867ea610f5f4717dfcefd0e730a42b9404b | punkti/0.6:2dc0696a81f0afaf69dddc2da34cc867ea610f5f4717dfcefd0e730a42b9404b |

## Divergences

- http_duplicate_key_divergence: HTTP envelope duplicate JSON keys: reference keeps the last records key and admits the record; clean-room rejects with HTTP 400 and stores nothing.
  - Reference: `{"addresses": ["punkti/0.6:fc23a2470534663943f5dc50e909a4e793accc3cf80586d16505a3733af95012"], "candidates": [], "http_status": 200, "log": [{"address": "punkti/0.6:fc23a2470534663943f5dc50e909a4e793accc3cf80586d16505a3733af95012", "seq": 1, "sha256": "f46c94caf3a3d36e62fd53cb1b60ac4ab4e53a23eb0523697b7e773046f0fd92"}], "response": {"results": [{"admitted": true, "state": "VALID"}]}}`.
  - Clean-room: `{"addresses": [], "candidates": [], "http_status": 400, "log": [], "response": {"kind": "request", "reason": "json"}}`.
- request_validation_divergences: Six pinned request-validation divergences: interval bounds, unknown query member, wrong address, and empty push batch.
  - GET /pull scope {h_lo:'g',h_hi:'g'}: reference HTTP 400, error 'empty/reversed h interval'; clean-room HTTP 200, records=[], end=true.
  - GET /pull scope {z_min:100,z_max:-100}: reference HTTP 400, error 'empty/reversed z interval'; clean-room HTTP 200, records=[], end=true.
  - GET /pull scope {z_min:1,z_max:1}: reference HTTP 400, error 'empty/reversed z interval'; clean-room HTTP 200, records=[], end=true.
  - GET /pull query {mode:'spatial',extra:1}: reference HTTP 200, member ignored; clean-room HTTP 400, kind='request', reason='query-fields'.
  - POST /push wrong address for a VALID record: reference HTTP 400 for the whole request, error 'address mismatch'; clean-room HTTP 200, per-record state='INVALID-structural', reason='address-mismatch', admitted=false.
  - POST /push {records:[]}: reference HTTP 400, error 'push batch size'; clean-room HTTP 200, {results:[]}.
  - Reference: `{"empty push batch": {"http_status": 400, "response": {"error": "push batch size"}}, "equal elevation": {"http_status": 400, "response": {"error": "empty/reversed z interval"}}, "equal h bounds": {"http_status": 400, "response": {"error": "empty/reversed h interval"}}, "reversed elevation": {"http_status": 400, "response": {"error": "empty/reversed z interval"}}, "unknown query member": {"http_status": 200, "response": {"cursor": {"after": 0, "ceiling": 0, "epoch": "<epoch>", "scope": "c6747acb328a79c07e24f7c1401f39b941bc5f8407a06acfb166b24d6ec98659"}, "end": true, "records": []}}, "wrong address for VALID record": {"http_status": 400, "response": {"error": "address mismatch"}}}`.
  - Clean-room: `{"empty push batch": {"http_status": 200, "response": {"results": []}}, "equal elevation": {"http_status": 200, "response": {"cursor": {"after": 0, "ceiling": 0, "epoch": "<epoch>", "scope": "9f9da9835f2129592facf29cdde29d28ce3afd9c38ce76719515e5af4c1e939f"}, "end": true, "records": []}}, "equal h bounds": {"http_status": 200, "response": {"cursor": {"after": 0, "ceiling": 0, "epoch": "<epoch>", "scope": "eeb3ceba4bc053f593dbe5c039f52cd0a54bcb5b4d85d8f0a2bc84ff39295bb7"}, "end": true, "records": []}}, "reversed elevation": {"http_status": 200, "response": {"cursor": {"after": 0, "ceiling": 0, "epoch": "<epoch>", "scope": "f7848f2c8f3f74503894880796c4aa86ece79a3219796d157cbd4e85c3d5bf12"}, "end": true, "records": []}}, "unknown query member": {"http_status": 400, "response": {"kind": "request", "reason": "query-fields"}}, "wrong address for VALID record": {"http_status": 200, "response": {"results": [{"admitted": false, "reason": "address-mismatch", "state": "INVALID-structural"}]}}}`.

Exact compared values and raw HTTP evidence are in `interop_report.json`.
