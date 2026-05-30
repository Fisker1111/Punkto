export async function fetchJsonWithTimeout(url, timeoutMs, options = {}) {
  const res = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(timeoutMs),
  });
  return res;
}

export async function postAtomToNetwork(atomBody, registry) {
  const { candidates, writeIndex } = registry.getWriteCandidateNodes();
  if (candidates.length === 0) throw new Error('No healthy nodes available');

  let firstError = null;

  for (let i = 0; i < candidates.length; i++) {
    const url = candidates[(writeIndex + i) % candidates.length];
    try {
      const res = await fetchJsonWithTimeout(`${url}/atom`, 10_000, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(atomBody),
      });
      if (!res.ok) {
        let detail = null;
        try { detail = await res.json(); } catch {}
        const message = detail?.message || detail?.error || `HTTP ${res.status}`;
        const err = new Error(message);
        err.status = res.status;
        err.code = detail?.error || null;
        err.detail = detail;
        throw err;
      }
      registry.markNodeSuccess(url);
      registry.commitWriteSuccess(candidates.length);
      return await res.json();
    } catch (e) {
      console.warn(`[lb] postAtom failed for ${url}:`, e.message);
      if (!firstError) firstError = e;
      registry.markNodeFailure(url);
      if (e.status && e.status < 500) break;
    }
  }

  throw firstError || new Error('All nodes failed');
}

export async function fetchNodeCursor(url) {
  try {
    const res = await fetchJsonWithTimeout(`${url}/feed?cursor=9999999999`, 6_000);
    if (!res.ok) return null;
    const json = await res.json();
    return typeof json.cursor === 'number' ? json.cursor : null;
  } catch {
    return null;
  }
}

export async function fetchNodeInfo(url) {
  try {
    const res = await fetchJsonWithTimeout(`${url}/info`, 6_000);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
