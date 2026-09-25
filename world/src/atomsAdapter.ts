export interface WorldAtom {
  id: string;
  x: number;
  y: number;
  altitudeM: number;
  t: number;
  message: string;
  identity?: string;
  color: string;
}
export interface Bounds { minLon: number; maxLon: number; minLat: number; maxLat: number }
export interface TimeWindow { from: number; to: number }
export interface AtomAdapter {
  getAtoms(bounds: Bounds, time: TimeWindow): Promise<WorldAtom[]>;
}
export const FIXTURE_START = Date.UTC(2026, 8, 25, 6);
export const FIXTURE_END = Date.UTC(2026, 8, 25, 23);
// FIXTURE DATA ONLY. Fixed coordinates and timestamps, never relay or stored user data.
const places: [string, number, number, number, string, string][] = [
  ['City Hall', 12.5683, 55.6761, 32, 'The city wakes in layers. Bells first, bicycles next.', 'Signe'],
  ['Tivoli', 12.5681, 55.6737, 24, 'A little light left over from last night.', 'Emil'],
  ['Nyhavn', 12.5908, 55.6798, 18, 'Stay here long enough and the water borrows every colour.', 'Freja'],
  ['Rundetårn', 12.5759, 55.6814, 35, 'Above the roofs, the city finally goes quiet.', 'Mikkel'],
  ['The Lakes', 12.5612, 55.6862, 12, 'The same loop. A different sky.', 'Alma'],
  ['Christiania', 12.6003, 55.6736, 15, 'A path that asks you to slow down.', 'Noor'],
  ['Amager Strand', 12.6475, 55.6596, 9, 'Wind from the east. Salt on everything.', 'Jonas'],
  ['Black Diamond', 12.5825, 55.6734, 28, 'A thousand stories facing the harbour.', 'Liv'],
  ['Christiansborg', 12.5804, 55.6763, 42, 'Look up. There is another city above this one.', 'Asta'],
  ['Nørreport', 12.5711, 55.6837, 20, 'Everyone arriving. Everyone going somewhere.', 'Oscar'],
  ['Botanical Garden', 12.5731, 55.6872, 16, 'Warm glass, green shadows, a pause.', 'Ida'],
  ['King’s Garden', 12.5808, 55.6852, 11, 'This patch of light belongs to the afternoon.', 'Elias'],
  ['Islands Brygge', 12.5777, 55.6685, 14, 'The first brave swimmer has already been.', 'Sofia'],
  ['Dronning Louises Bro', 12.5603, 55.6885, 19, 'Meet me where the bicycles become a river.', 'Malik'],
  ['Opera House', 12.6006, 55.6818, 38, 'Across the water, a room full of sound.', 'Clara'],
  ['Kongens Nytorv', 12.5854, 55.6805, 23, 'All these streets begin with a small decision.', 'Anton'],
  ['Gammel Strand', 12.5787, 55.6775, 17, 'The stone steps still hold the sun.', 'Naja'],
  ['Vesterbro', 12.5549, 55.6708, 13, 'Coffee outside, even when it is too cold.', 'Theo'],
];
export const fixtureAtoms: readonly WorldAtom[] = places.map(([place, x, y, altitudeM, message, identity], i) => ({
  id: `world-fixture-${i + 1}`, x, y, altitudeM,
  t: FIXTURE_START + i * 60 * 60 * 1000,
  message: `${message} — ${place}`, identity,
  color: ['#f6bb78', '#8bd6cb', '#b8a4ef'][i % 3],
}));
export const fixtureAdapter: AtomAdapter = {
  async getAtoms(bounds, time) {
    return fixtureAtoms.filter(a => a.x >= bounds.minLon && a.x <= bounds.maxLon &&
      a.y >= bounds.minLat && a.y <= bounds.maxLat && a.t >= time.from && a.t <= time.to);
  },
};
