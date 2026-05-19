export function createNodeRegistry({ nodeUrl, seedNodes }) {
  const nodeRegistry = new Map();
  let writeIndex = 0;

  function initNodeRegistry() {
    const allNodes = new Set([nodeUrl, ...seedNodes]);
    allNodes.forEach(url => {
      if (!nodeRegistry.has(url)) {
        nodeRegistry.set(url, { health: 'ok', failures: 0, unavailableSince: 0 });
      }
    });
  }

  function getHealthyNodes() {
    const now = Date.now();
    return [...nodeRegistry.entries()]
      .filter(([, s]) => {
        if (s.health === 'ok' || s.health === 'failing') return true;
        if (s.health === 'recovering') return true;
        if (s.health === 'unavailable' && now - s.unavailableSince > 60_000) {
          s.health = 'recovering';
          return true;
        }
        return false;
      })
      .map(([url]) => url);
  }

  function markNodeSuccess(url) {
    const s = nodeRegistry.get(url);
    if (s) { s.health = 'ok'; s.failures = 0; s.unavailableSince = 0; }
  }

  function markNodeFailure(url) {
    const s = nodeRegistry.get(url);
    if (!s) return;
    s.failures++;
    if (s.failures >= 5) {
      s.health = 'unavailable';
      s.unavailableSince = Date.now();
    } else if (s.failures >= 2) {
      s.health = 'failing';
    }
  }

  function getWriteCandidateNodes() {
    const candidates = getHealthyNodes();
    return { candidates, writeIndex };
  }

  function commitWriteSuccess(candidateCount) {
    writeIndex = (writeIndex + 1) % candidateCount;
  }

  return {
    initNodeRegistry,
    getHealthyNodes,
    markNodeSuccess,
    markNodeFailure,
    getWriteCandidateNodes,
    commitWriteSuccess,
    hasNode: (url) => nodeRegistry.has(url),
    registerNode: (url) => nodeRegistry.set(url, { health: 'ok', failures: 0, unavailableSince: 0 }),
    keys: () => nodeRegistry.keys(),
    getNodeSnapshot: () => [...nodeRegistry.entries()].map(([url, state]) => ({
      url,
      health: state.health,
      failures: state.failures,
      unavailableSince: state.unavailableSince,
    })),
  };
}
