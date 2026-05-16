import { db } from './db.js';

export async function getStoredNodes() {
  return db.nodes.toArray();
}

export async function getNodeByUrl(url) {
  return db.nodes.get(url);
}

export async function putNode(node) {
  return db.nodes.put(node);
}

export async function ensureNode(url, cursor = 0) {
  const existing = await db.nodes.get(url);
  if (!existing) {
    await db.nodes.put({ url, cursor });
    return true;
  }
  return false;
}
