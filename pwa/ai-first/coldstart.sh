#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
  echo "Usage: coldstart.sh http://127.0.0.1:PORT/nodes.json" >&2
  exit 1
fi
# Fixed /tmp avoids a caller's TMPDIR accidentally putting secrets in a checkout.
work=$(mktemp -d /tmp/punkti-coldstart.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
export PUNKTO_LOCAL_ONLY=1
node --input-type=module - "$1" "$work" <<'JS'
import { mkdir, writeFile, realpath, access } from 'node:fs/promises';
import path from 'node:path';
const [nodes, destination] = process.argv.slice(2);
const url = new URL(nodes);
if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.username || url.password) throw new Error('Stage 0 cold-start allows only local HTTP at 127.0.0.1; future staging needs separate authorization');
let ancestor = await realpath(destination);
while (ancestor !== path.dirname(ancestor)) {
  let checkout = false;
  try { await access(path.join(ancestor, '.git')); checkout = true; } catch {}
  if (checkout) throw new Error('refusing to write client or key into a repository');
  ancestor = path.dirname(ancestor);
}
for (const file of ['ai-first/index.html', 'ai-first/agent.mjs', 'punkti/carrier.js', 'punkti/spatial.js', 'punkti/reader.js', 'punkti/submit.js', 'nacl.min.js']) {
  const address = new URL('/' + file, url);
  const response = await fetch(address, { redirect: 'error', signal: AbortSignal.timeout(10000) });
  const bytes = new Uint8Array(await response.arrayBuffer());
  console.error(`HTTP GET ${address} -> ${response.status} bytes=${bytes.length}`);
  if (!response.ok) throw new Error(`cannot fetch client ${file}`);
  await mkdir(path.dirname(path.join(destination, file)), { recursive: true });
  await writeFile(path.join(destination, file), bytes);
}
JS
cd "$work"
echo 'Scripted harness, not a blind-AI experiment; fresh client-only temporary directory.'
node ai-first/agent.mjs boot --nodes "$1"
node ai-first/agent.mjs discover --nodes "$1" > discovery.json
cat discovery.json
h=$(node --input-type=module -e 'import fs from "node:fs"; const d=JSON.parse(fs.readFileSync("discovery.json")); console.log(d.candidates[0]?.h ?? "u3butz7k9q_23")')
echo "Chosen destination: $h (if publication empty, explicitly chosen harness address u3butz7k9q_23; never a height measurement)."
node ai-first/agent.mjs publish --nodes "$1" --h "$h" --text 'Stage 0 local cold-start scripted evidence' --key-file "$work/identity.seed" > receipt.json
cat receipt.json
mid=$(node --input-type=module -e 'import fs from "node:fs"; console.log(JSON.parse(fs.readFileSync("receipt.json")).mid)')
node ai-first/agent.mjs verify --nodes "$1" --mid "$mid" --h "$h"
