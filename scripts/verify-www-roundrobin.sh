#!/usr/bin/env bash
# Read-only remote probes; only temporary local response files are written.
set -euo pipefail
usage() {
    cat <<'HELP'
Usage: verify-www-roundrobin.sh [--help]
Read-only probes of each www origin by IP with correct SNI, and public DNS.
Overrides: WWW_HOST=www.punkto.xyz NODE1_IP=46.101.118.157
           NODE2_IP=159.65.115.166 TIMEOUT=8 (seconds per network operation).
Requires bash, curl, openssl, timeout, dig, python3, cmp, mktemp.
POST /submit and /api/submit use the deliberately malformed tiny JSON body "{"
so no record can be created. No other POSTs, DNS changes or service operations.
Local temporary response files are removed on exit. No TLS bypass or redirects.
Every failed hard check contributes to exit 1, including publication divergence.
An explicit founder divergence exception must be recorded separately.
HELP
}
if [[ ${1:-} == --help || ${1:-} == -h ]]; then usage; exit 0; fi
if (( $# )); then usage >&2; exit 2; fi
WWW_HOST=${WWW_HOST:-www.punkto.xyz}
NODE1_IP=${NODE1_IP:-46.101.118.157}
NODE2_IP=${NODE2_IP:-159.65.115.166}
TIMEOUT=${TIMEOUT:-8}
passed=0 failed=0
pass() { printf 'PASS %s\n' "$*"; passed=$((passed + 1)); }
fail() { printf 'FAIL %s\n' "$*"; failed=$((failed + 1)); }
summary() { printf 'SUMMARY PASS=%s FAIL=%s\n' "$passed" "$failed"; }
if [[ ! $TIMEOUT =~ ^[1-9][0-9]*$ ]]; then fail 'TIMEOUT must be a positive integer'; summary; exit 1; fi
for command in curl openssl timeout dig python3 cmp mktemp; do
    if ! command -v "$command" >/dev/null; then fail "missing dependency: $command"; fi
done
if (( failed )); then summary; exit 1; fi
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
paths=(/ /ai /publication/root.json /nodes.json /health /mcp)
for node in 1 2; do
    ip=$NODE1_IP
    if [[ $node == 2 ]]; then ip=$NODE2_IP; fi
    label="node$node ($ip)"
    if timeout "$TIMEOUT" openssl s_client -connect "$ip:443" -servername "$WWW_HOST" \
        -verify_hostname "$WWW_HOST" -verify_return_error -showcerts </dev/null \
        >"$tmp/tls$node" 2>"$tmp/tls$node.err"; then
        pass "$label TLS handshake, trusted chain and hostname"
    else
        fail "$label TLS handshake, trusted chain or hostname (unavailable/invalid/timeout)"
    fi
    if openssl x509 -in "$tmp/tls$node" -noout -ext subjectAltName >"$tmp/san$node" 2>/dev/null &&
        python3 - "$tmp/san$node" "$WWW_HOST" <<'PY'
import pathlib, sys
names = pathlib.Path(sys.argv[1]).read_text().replace(',', ' ').split()
host = sys.argv[2].lower()
sys.exit(0 if any(n.lower() == 'dns:' + host or
    (n.lower().startswith('dns:*.') and host.split('.', 1)[-1] == n[6:].lower())
    for n in names) else 1)
PY
    then pass "$label certificate SAN covers $WWW_HOST"
    else fail "$label certificate SAN missing or does not cover $WWW_HOST"; fi
    if openssl x509 -in "$tmp/tls$node" -noout -checkend 0 >/dev/null 2>&1; then
        expiry=$(openssl x509 -in "$tmp/tls$node" -noout -enddate)
        pass "$label certificate expiry $expiry"
    else fail "$label certificate expired or unavailable"; fi
    for index in "${!paths[@]}"; do
        path=${paths[$index]}
        expected=200
        if [[ $path == /mcp ]]; then expected=405; fi
        if status=$(curl --noproxy '*' --silent --show-error --connect-timeout "$TIMEOUT" \
            --max-time "$TIMEOUT" --resolve "$WWW_HOST:443:$ip" \
            -o "$tmp/$node-$index" -w '%{http_code}' "https://$WWW_HOST$path" 2>"$tmp/curl.err"); then
            if [[ $status == "$expected" ]]; then
                pass "$label GET $path HTTP $status"
                touch "$tmp/$node-$index.ok"
            else fail "$label GET $path HTTP $status (expected $expected)"; fi
        else fail "$label GET $path transport/TLS failure (HTTP $status)"; fi
    done
    for path in /submit /api/submit; do
        if status=$(curl --noproxy '*' --silent --show-error --connect-timeout "$TIMEOUT" \
            --max-time "$TIMEOUT" --resolve "$WWW_HOST:443:$ip" \
            -H 'Content-Type: application/json' --data-binary '{' \
            -o /dev/null -w '%{http_code}' "https://$WWW_HOST$path" 2>"$tmp/curl.err"); then
            if [[ $status == 403 ]]; then pass "$label POST $path HTTP 403 (malformed probe)"
            else fail "$label POST $path HTTP $status (expected 403)"; fi
        else fail "$label POST $path transport/TLS failure (HTTP $status)"; fi
    done
done
for index in 0 1 4; do
    path=${paths[$index]}
    if [[ ! -f $tmp/1-$index.ok || ! -f $tmp/2-$index.ok ]]; then
        fail "body parity $path unavailable (both successful responses required)"
    elif cmp -s "$tmp/1-$index" "$tmp/2-$index"; then pass "body parity $path identical"
    else fail "body parity $path different"; fi
done
if [[ -f $tmp/1-2.ok && -f $tmp/2-2.ok ]]; then
    if result=$(python3 - "$tmp/1-2" "$tmp/2-2" <<'PY'
import json, sys
try:
    roots = [json.load(open(p)) for p in sys.argv[1:]]
    for r in roots:
        assert isinstance(r['head'], str) and len(r['head']) == 64
        assert all(c in '0123456789abcdef' for c in r['head'])
        assert type(r['seq']) is int and r['seq'] >= 0
    print('publication heads: ' + '; '.join(f"node{i}: head={r['head']} seq={r['seq']}" for i, r in enumerate(roots, 1)))
    sys.exit(0 if (roots[0]['head'], roots[0]['seq']) == (roots[1]['head'], roots[1]['seq']) else 1)
except (ValueError, KeyError, TypeError, AssertionError):
    print('invalid publication root JSON/head/seq')
    sys.exit(1)
PY
    ); then pass "$result (converged)"
    else fail "$result (publication-chain divergence or invalid root)"; fi
else fail 'publication-chain comparison unavailable; divergence cannot be cleared'; fi
for resolver in 1.1.1.1 8.8.8.8 9.9.9.9; do
    for type in A CNAME; do
        if dig "@$resolver" "$WWW_HOST" "$type" +time="$TIMEOUT" +tries=1 +noall +comments +answer \
            >"$tmp/dns-$type" 2>&1; then
            :
        else printf '\nQUERY_FAILED\n' >>"$tmp/dns-$type"; fi
    done
    if result=$(python3 - "$tmp/dns-A" "$tmp/dns-CNAME" "$NODE1_IP" "$NODE2_IP" <<'PY'
import pathlib, sys
texts = [pathlib.Path(p).read_text() for p in sys.argv[1:3]]
records = [line.split() for text in texts for line in text.splitlines() if line and not line.startswith(';')]
a = sorted({r[4] for r in records if len(r) >= 5 and r[3] == 'A'})
cname = sorted({r[4] for r in records if len(r) >= 5 and r[3] == 'CNAME'})
print(f'A={a} CNAME={cname}')
ok = all('status: NOERROR' in t and 'QUERY_FAILED' not in t for t in texts)
sys.exit(0 if ok and a == sorted(set(sys.argv[3:5])) and not cname else 1)
PY
    ); then pass "resolver $resolver target topology $result"
    else fail "resolver $resolver target topology $result (requires both A records, no CNAME, successful queries)"; fi
done
summary
(( failed == 0 ))
