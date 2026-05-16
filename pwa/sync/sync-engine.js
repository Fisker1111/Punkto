import { getStoredNodes, ensureNode } from '../storage/node-store.js';
import { upsertAtom } from '../storage/atom-store.js';
import { fetchJsonWithTimeout } from './network-client.js';

export function createSyncEngine({
  nodeUrl,
  seedNodes,
  syncIntervalMs,
  nodeRegistry,
  isHiddenAtom,
  callbacks = {},
}) {
  let syncTimer = null;
  let syncing = false;

  const onSyncStart = callbacks.onSyncStart || (() => {});
  const onSyncDone = callbacks.onSyncDone || (() => {});
  const onSyncError = callbacks.onSyncError || (() => {});
  const onAtomsChanged = callbacks.onAtomsChanged || (async () => {});
  const onPeersChanged = callbacks.onPeersChanged || (async () => {});

  async function syncFeed() {
    if (syncing) return;
    syncing = true;
    onSyncStart();

    let anyError = false;
    const newAtomIds = new Set();

    try {
      const storedNodes = await getStoredNodes();
      const nodeUrls = new Set(storedNodes.map(n => n.url));
      nodeUrls.add(nodeUrl);

      for (const url of nodeUrls) {
        try {
          const res = await fetchJsonWithTimeout(`${url}/latest`, 15_000);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();

          if (Array.isArray(data.atoms) && data.atoms.length > 0) {
            for (const atom of data.atoms) {
              if (atom.punkto && atom.t) {
                const r = await upsertAtom(atom);
                if (r && r.inserted && !isHiddenAtom(atom)) {
                  newAtomIds.add(r.id);
                }
              }
            }
          }
        } catch (nodeErr) {
          console.warn(`[sync] latest error for ${url}:`, nodeErr);
          anyError = true;
        }
      }

      await onAtomsChanged(newAtomIds);
      onSyncDone({ anyError });
    } catch (err) {
      console.warn('[sync] unexpected error:', err);
      onSyncError(err);
    } finally {
      syncing = false;
    }
  }

  async function discoverPeers() {
    for (const seedUrl of nodeRegistry.keys()) {
      try {
        const res = await fetchJsonWithTimeout(`${seedUrl}/info`, 8_000);
        if (!res.ok) continue;
        const info = await res.json();
        const peers = Array.isArray(info.peers) ? info.peers : [];
        let changed = false;
        for (const peerUrl of peers) {
          const url = peerUrl.replace(/\/$/, '');
          if (!url) continue;
          if (!nodeRegistry.hasNode(url)) {
            nodeRegistry.registerNode(url);
            changed = true;
            console.log('[lb] discovered peer:', url);
          }
          await ensureNode(url, 0);
        }
        if (changed) await onPeersChanged();
      } catch (err) {
        console.warn(`[lb] peer discovery error for ${seedUrl}:`, err.message);
      }
    }
  }

  function start() {
    if (syncTimer) return;
    syncTimer = setInterval(syncFeed, syncIntervalMs);
  }

  function stop() {
    if (!syncTimer) return;
    clearInterval(syncTimer);
    syncTimer = null;
  }

  function isSyncing() {
    return syncing;
  }

  return { syncFeed, discoverPeers, start, stop, isSyncing };
}
