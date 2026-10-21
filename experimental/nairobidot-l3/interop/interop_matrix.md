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
| no_reference_imports | PASS | 30 recorded comparisons; Static scan and isolated import prove clean-room source independence. |
| push_both_directions | PASS | 33 recorded comparisons; Both HTTP push directions admit VALID and return identical R/digests. |
| rejection_consistency | FAIL | 157 recorded comparisons; Malformed/forged records stay out of main store; valid later wins. |
| spatial_range_selection | PASS | 74 recorded comparisons; Literal half-open h bounds filter push admission and peer PULL. |
| unknown_l4_byte_preservation | PASS | 85 recorded comparisons; Unicode, JSON-looking text, unknown refs/ext/alg survive exact transfer. |
| vector_parity | PASS | 67 recorded comparisons; Six deterministic vectors compare all canonical and framed bytes. |
| xy_z_selection | PASS | 66 recorded comparisons; Fixed XY bits with varying Z agree at exact altitude boundaries. |

Totals: 10 PASS, 1 FAIL.

| Vector | MID | Address |
|---|---|---|
| unanchored | 87bd4380e5580124d46e4a4a43192d8afa3b5a0855ae90e0b564d713e10abfa8 | punkti/0.6:87bd4380e5580124d46e4a4a43192d8afa3b5a0855ae90e0b564d713e10abfa8 |
| XY | 7a1e1d6e9b4b1a0637bcacd771758619555f419c881797e1730d59e01f7f6301 | punkti/0.6:7a1e1d6e9b4b1a0637bcacd771758619555f419c881797e1730d59e01f7f6301 |
| XYZ | f7d9dafe4d2bbeaafe7367db1d9b40762760abae0a096ac624a60e9e27579fca | punkti/0.6:f7d9dafe4d2bbeaafe7367db1d9b40762760abae0a096ac624a60e9e27579fca |
| refs-order-duplicates | 37016dd1af177b43a5f5a1991603dc9438bb8f149b729020b50d79e35d04049d | punkti/0.6:37016dd1af177b43a5f5a1991603dc9438bb8f149b729020b50d79e35d04049d |
| unicode-ext | 8d72c892016d6db3e4017383bddc7a0acb9314e72ca69dab5c62fbc3294293cd | punkti/0.6:8d72c892016d6db3e4017383bddc7a0acb9314e72ca69dab5c62fbc3294293cd |
| unknown-alg | 2dc0696a81f0afaf69dddc2da34cc867ea610f5f4717dfcefd0e730a42b9404b | punkti/0.6:2dc0696a81f0afaf69dddc2da34cc867ea610f5f4717dfcefd0e730a42b9404b |

## Divergences

- rejection_consistency: duplicate JSON keys HTTP rejection ref: actual=200; expected=400; duplicate JSON keys main store ref: actual=['punkti/0.6:fc23a2470534663943f5dc50e909a4e793accc3cf80586d16505a3733af95012']; expected=[]
- Duplicate-key request responses (reference, clean-room): `[[200, {"results": [{"admitted": true, "state": "VALID"}]}], [400, {"kind": "request", "reason": "json"}]]`.

Exact compared values and raw HTTP evidence are in `interop_report.json`.
