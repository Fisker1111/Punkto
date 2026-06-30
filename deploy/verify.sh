#!/usr/bin/env bash
# Punkto post-deploy smoke-test script.
# Usage: bash deploy/verify.sh <node-host> <expected-hard-marker>
# Example: bash deploy/verify.sh node1.punkto.xyz "v86-hard-marker-2026-05-25-1"

set -euo pipefail

NODE="${1:?usage: verify.sh <node-host> <expected-marker>}"
MARKER="${2:?usage: verify.sh <node-host> <expected-marker>}"

FAIL=0
pass() { printf "  ✅  %s\n" "$1"; }
fail() { printf "  ❌  %s\n" "$1"; FAIL=1; }

echo "🔎 Punkto smoke tests — $NODE"
echo "   expected marker: $MARKER"
echo

# 1. Hard marker
if curl -sS -H 'Cache-Control: no-cache' "https://${NODE}/app.js" | grep -Fq "$MARKER"; then
  pass "hard marker present in app.js"
else
  fail "hard marker MISSING in app.js"
fi

# 2. Cache-Control
CC=$(curl -sS -I "https://${NODE}/app.js" | tr -d '\r' | grep -i '^cache-control:' || true)
if echo "$CC" | grep -qi 'no-cache, no-store, must-revalidate'; then
  pass "Cache-Control strict

$CC"
else
  fail "Cache-Control unexpected: ${CC:-<empty>}"
fi

# 3. PWA icons
for sz in 192 512; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" "https://${NODE}/logo-${sz}.png")
  if [[ "$code" == "200" ]]; then
    pass "logo-${sz}.png -> 200"
  else
    fail "logo-${sz}.png -> $code"
  fi
done

# 4. Relay /health
HEALTH=$(curl -sS -o /tmp/health.json -w "%{http_code}" "https://${NODE}/health" || true)
if [[ "$HEALTH" == "200" ]]; then
  pass "relay /health -> 200 ($(cat /tmp/health.json | head -c 120))"
else
  fail "relay /health -> ${HEALTH:-timeout}"
fi

# 5. Relay /feed
FEED=$(curl -sS -o /dev/null -w "%{http_code}" "https://${NODE}/feed?limit=1" || true)
if [[ "$FEED" == "200" ]]; then
  pass "relay /feed -> 200"
else
  fail "relay /feed -> ${FEED:-timeout}"
fi

# 6. index.html title
TITLE=$(curl -sS "https://${NODE}/" | grep -oE '<title>[^<]*</title>' | head -1 || true)
if [[ -n "$TITLE" ]]; then
  pass "index.html $TITLE"
else
  fail "index.html missing <title>"
fi

echo
if [[ $FAIL -eq 0 ]]; then
  echo "🟢 All smoke tests PASSED on $NODE"
  exit 0
else
  echo "🔴 One or more smoke tests FAILED on $NODE"
  exit 1
fi
