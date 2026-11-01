# Independent custody of the C1 records

The custodian must hold the exact raw canonical R bytes of the ROOT and REPLY
and prove those copies independently of the Punkto operator's servers. The
custodian must be a different party with its own storage and administrative
authority. A second copy on the Punkto operator's infrastructure does not count.

## Records

Both records have `h = s00000000000_0`.

| Record | MID | Record SHA-256 | Plain-GET URL |
| --- | --- | --- | --- |
| ROOT | `punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed` | `2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d` | https://punkto.xyz/publication/records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d |
| REPLY | `punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854` | `0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b` | https://punkto.xyz/publication/records/0c/0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b |

## Rules and tools

Store the response-body bytes unmodified. Never edit, re-sign, re-serialize,
re-MID, decompress or base64-decode the records. File names are arbitrary; the
bytes must remain byte-identical. Ed25519 authorship is real in the sense of a
valid signature under the recorded public key; it does not verify a person's
identity and is not post-quantum security. Do not claim either verified identity
or post-quantum security.

Use a plain HTTP GET and `scripts/qa/custody_verify.py` from a repository checkout.
The tool needs Python 3.11+ and `cryptography` (already a node dependency), plus the
checkout's `punkti_node/carrier.py` and `punkti_node/spatial.py`. Run the following
from the repository root. No secrets, API keys or tokens are needed.

If Python is unavailable, `sha256sum root.R reply.R` checks the raw file digests
against the table. MID, canonical-body, spatial-address, signature and reply-link
checks additionally require a Punkti 0.6 validator; SHA-256 alone does not perform
those checks.

## Fetch and verify

```bash
ROOT_URL='https://punkto.xyz/publication/records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d'
REPLY_URL='https://punkto.xyz/publication/records/0c/0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b'
ROOT_MID='punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed'
REPLY_MID='punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854'
ROOT_SHA='2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d'
REPLY_SHA='0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b'
curl --fail --silent --show-error -H 'Accept-Encoding: identity' "$ROOT_URL" -o root.R
curl --fail --silent --show-error -H 'Accept-Encoding: identity' "$REPLY_URL" -o reply.R
python3 scripts/qa/custody_verify.py --file root.R \
  --expect-sha256 "$ROOT_SHA" --expect-mid "$ROOT_MID" --expect-h s00000000000_0
python3 scripts/qa/custody_verify.py --file reply.R \
  --expect-sha256 "$REPLY_SHA" --expect-mid "$REPLY_MID" --expect-h s00000000000_0 \
  --expect-reply-of "$ROOT_MID"
```

Both verifier commands must exit 0. Each emits one JSON line on stdout and a
summary on stderr. Expected fields are `state: "VALID"`, `ed25519: "VALID"`,
`canonical_body: true`, `ok: true`, the MID and SHA-256 from the table, and
`h: "s00000000000_0"`. ROOT has `refs: []`; REPLY has:

```json
[{"target":"punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed","rel":"reply"}]
```

All applicable entries in `expectations` must be true. To verify live response
bodies directly, replace `--file root.R` with `--url "$ROOT_URL"` and similarly
for REPLY. Direct URL verification does not save a custody copy. Multiple files
or URLs, including mixed options, are processed in command-line order. Each
supplied expectation option must occur once per input; use separate invocations
as above to apply the reply expectation only to REPLY.

The `payload_digest_base32_sha1` field is the uppercase base32 SHA-1 of the raw
bytes without `=` padding. It can be compared to an Internet Archive CDX payload
digest, without trusting that index for other claims. It does not replace SHA-256
or signature verification.

## Origin-outage drill

Run this only on an isolated test client, never on production servers. Do not
change DNS or touch production. Store copies on the custodian's own infrastructure
first. On this client, block access to both `punkto.xyz` and `test2.punkto.xyz`
for every fetch in the drill. For curl, a test-only wrapper is:

```bash
isolated_get() {
  curl --noproxy '*' --connect-timeout 5 --max-time 30 \
    --connect-to punkto.xyz:443:127.0.0.1:1 \
    --connect-to test2.punkto.xyz:443:127.0.0.1:1 \
    --connect-to punkto.xyz:80:127.0.0.1:1 \
    --connect-to test2.punkto.xyz:80:127.0.0.1:1 \
    --fail --silent --show-error -H 'Accept-Encoding: identity' "$@"
}
isolated_get "$ROOT_URL" -o blocked-origin.R
isolated_get 'https://test2.punkto.xyz/' -o blocked-secondary.R
```

Both probes must fail to connect; ensure port 1 on the test client has no listener.
These per-command routes affect only the test client and do not change DNS.
Then set `CUSTODIAN_ROOT_URL` and `CUSTODIAN_REPLY_URL` to the custodian's public
raw-copy URLs, served directly without redirects or origin fallback:

```bash
isolated_get "$CUSTODIAN_ROOT_URL" -o restored-root.R
isolated_get "$CUSTODIAN_REPLY_URL" -o restored-reply.R
python3 scripts/qa/custody_verify.py --file restored-root.R \
  --expect-sha256 "$ROOT_SHA" --expect-mid "$ROOT_MID" --expect-h s00000000000_0
python3 scripts/qa/custody_verify.py --file restored-reply.R \
  --expect-sha256 "$REPLY_SHA" --expect-mid "$REPLY_MID" --expect-h s00000000000_0 \
  --expect-reply-of "$ROOT_MID"
```

Do not use the verifier's `--url` mode during this curl-based drill: the curl
routing overrides do not apply to Python. Keep origin access blocked for all
fetches, and verify the downloaded files offline. Successful checks demonstrate
retrieval from the custodian while this client cannot reach either origin.
They do not by themselves prove the custodian has no server-side origin dependency.

## Restore and durability drill

On a non-production test instance of the custodian's own store, stop and restart
the store using its documented service procedure. Re-read the retained files
from disk after restart; run the same `--file` checks above on those paths. Also
repeat retrieval through the isolated client. Retain outputs confirming identical
SHA-256, MID, signature and reply link before and after restart.

This demonstrates the custodian's own persistence through that restart and
availability during the tested client outage. It does not prove indefinite
retention, resilience to every failure, or the durability of a particular
third-party web archive. The verifier proves bytes, MID, signature and reply
link; it does not prove who controls a custodian account.

## How to report

Publish the stored raw-byte URLs, complete verification JSON Lines and exit
codes, UTC timestamps, failed-origin probe evidence, and before/after restart
results. Describe the independent operator's storage and administrative
authority and the consent or authority under which it holds the copies. No
secrets are needed; do not publish credentials or private keys.
