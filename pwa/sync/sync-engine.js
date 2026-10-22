import { upsertAtom } from '../storage/atom-store.js';
import { isValidAtom } from '../protocol/atom-validate.js';

export function createSyncEngine({ client, syncIntervalMs, isHiddenAtom, callbacks = {} }) {
  let timer = null, syncing = false;
  async function syncFeed() {
    if (syncing) return;
    syncing = true;
    callbacks.onSyncStart?.();
    try {
      const ids = new Set();
      for (const atom of await client.pullAll()) {
        if (!isValidAtom(atom)) continue;
        const result = await upsertAtom(atom);
        if (result?.inserted && !isHiddenAtom(atom)) ids.add(result.id);
      }
      await callbacks.onAtomsChanged?.(ids);
      callbacks.onSyncDone?.({ anyError: false });
    } catch (err) {
      callbacks.onSyncError?.(err);
      console.warn('[sync]', err);
    } finally { syncing = false; }
  }
  return { syncFeed, isSyncing: () => syncing,
    start() { if (!timer) timer = setInterval(syncFeed, syncIntervalMs); },
    stop() { clearInterval(timer); timer = null; } };
}
