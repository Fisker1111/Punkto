import { isQaRecord } from './read-state.js';

export const EXPLORE_PLACE_LIMIT = 2;

export function initialPageForBoot() {
  return 'map';
}

export function selectExplorePlaces(atoms, { limit = EXPLORE_PLACE_LIMIT } = {}) {
  const groups = new Map();
  for (const atom of atoms) {
    if (atom.relation === 'reply' || atom.parent_id) continue;
    if (!atom.h || !Number.isFinite(atom.lat) || !Number.isFinite(atom.lon)) continue;
    let group = groups.get(atom.h);
    if (!group) {
      group = { place: {
        atomId: atom.atom_id,
        h: atom.h,
        lat: atom.lat,
        lon: atom.lon,
        title: String(atom.x || '').split('\n')[0].trim(),
        kind: 'qa',
      }, count: 0 };
      groups.set(atom.h, group);
    }
    group.count++;
    if (!isQaRecord(atom)) group.place.kind = 'public';
  }
  const all = [...groups.values()];
  const kind = all.some(group => group.place.kind === 'public') ? 'public' : 'qa';
  return all.filter(group => group.place.kind === kind)
    .sort((a, b) => b.count - a.count || (a.place.h < b.place.h ? -1 : a.place.h > b.place.h ? 1 : 0))
    .slice(0, limit)
    .map(group => group.place);
}

export function primaryExplorePlace(places) {
  return places[0] || null;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

export function explorePlacesHtml(places) {
  return places.map(place => `<button type="button" class="ui-btn explore-place-button" data-action="explore-place" data-atom-id="${escapeHtml(place.atomId)}">${place.kind === 'qa' ? 'QA record · ' : ''}${escapeHtml(place.title)}<br><span>${escapeHtml(place.h)}</span></button>`).join('');
}

export function exploreNudgeBodyHtml(places, readState) {
  return places.length ? explorePlacesHtml(places)
    : readState === 'loading'
      ? '<p role="status">Loading published places…</p>'
      : readState === 'error'
        ? '<p role="status">Could not load published places. Try again.</p><button type="button" class="ui-btn explore-place-button" data-action="retry-read">Retry</button>'
        : '<p role="status">No published places in this scope.</p>';
}
