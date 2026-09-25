import { FIXTURE_START, FIXTURE_END, type WorldAtom } from './atomsAdapter';
const date = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Copenhagen', hour: '2-digit', minute: '2-digit' });
export function createUI(onTime: (to: number) => void, onHome: () => void, onSelect: (atom: WorldAtom) => void, onClose: () => void) {
  document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
    <header class="masthead"><a class="brand" href="/" aria-label="Punkto World home"><span class="brand-orb"></span>punkto<span class="world-word">world</span></a><span class="edition">EXPLORATION / 001</span></header>
    <section class="intro"><p class="eyebrow">DENMARK · 55.6761° N / 12.5683° E</p><h1>Copenhagen<span>, alive.</span></h1><p>Small stories. Real places. A world to wander.</p></section>
    <div class="world-tools"><button id="home" title="Return to Copenhagen">⌖ <span>Copenhagen</span></button><span class="fixture-badge">Fixture world</span></div>
    <p id="status" class="status" role="status">Opening the world…</p>
    <aside id="detail" class="detail" aria-label="Atom details" hidden tabindex="-1"><button id="close" class="close" aria-label="Close atom details">×</button><p class="eyebrow">A MESSAGE EXISTS HERE</p><p id="message" class="message"></p><div class="byline"><span id="avatar"></span><span id="identity"></span><time id="timestamp"></time></div><div id="location" class="location"></div></aside>
    <section class="timeline" aria-label="Time exploration"><div class="timeline-top"><div><p class="eyebrow">EXPLORE THROUGH TIME</p><span class="day">25 September 2026</span></div><output id="time" for="time-slider"></output></div><label class="sr-only" for="time-slider">Show messages posted up to this time, Copenhagen time</label><input id="time-slider" type="range" min="0" max="17" value="17" step="1"><div class="timeline-bottom"><span>08:00</span><span id="count" aria-live="polite"></span><span>01:00 +1d</span></div><details class="nearby"><summary>Explore visible messages</summary><div id="atom-list"></div></details></section>
    <p class="gesture-hint">Drag to wander · Scroll to explore · Right-drag to tilt & rotate</p>`;
  const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const slider = el<HTMLInputElement>('time-slider');
  const updateTime = () => {
    const to = FIXTURE_START + Number(slider.value) * 3600000;
    el<HTMLOutputElement>('time').textContent = `${date.format(to)}${to === FIXTURE_END ? ' +1d' : ''} CPH`;
    slider.setAttribute('aria-valuetext', `Messages through ${date.format(to)} Copenhagen time`);
    return to;
  };
  updateTime();
  slider.addEventListener('input', () => onTime(updateTime()));
  el('home').addEventListener('click', onHome);
  el('close').addEventListener('click', onClose);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') onClose(); });
  return {
    status(message: string) { el('status').textContent = message; },
    atoms(atoms: WorldAtom[]) {
      el('count').textContent = `${atoms.length} ${atoms.length === 1 ? 'message' : 'messages'} in view`;
      el('atom-list').replaceChildren(...atoms.map(atom => {
        const button = document.createElement('button');
        button.textContent = `${atom.identity} · ${atom.message.split(' — ').at(-1)}`;
        button.addEventListener('click', () => onSelect(atom));
        return button;
      }));
    },
    detail(atom: WorldAtom | null) {
      const panel = el('detail');
      const wasFocused = panel.contains(document.activeElement);
      panel.hidden = !atom;
      if (!atom) { if (wasFocused) el('home').focus(); return; }
      panel.style.setProperty('--atom-color', atom.color);
      el('message').textContent = atom.message;
      el('identity').textContent = atom.identity ?? 'Anonymous';
      el('avatar').textContent = (atom.identity ?? '?').slice(0, 1);
      el('timestamp').textContent = `${date.format(atom.t)} CPH`;
      el('timestamp').setAttribute('datetime', new Date(atom.t).toISOString());
      el('location').textContent = `${atom.y.toFixed(4)}° N, ${atom.x.toFixed(4)}° E · ${atom.altitudeM} m above ground`;
      panel.focus({ preventScroll: true });
    },
  };
}
