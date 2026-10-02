import { type TimeWindow, type WorldAtom } from './atomsAdapter';
const date = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Copenhagen', hour: '2-digit', minute: '2-digit' });
export function createUI(onTime: (to: number) => void, onHome: () => void, onSelect: (atom: WorldAtom) => void, onClose: () => void, onTheme: () => void, window: TimeWindow, useFixtures: boolean) {
  document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
    <header class="masthead"><a class="brand" href="/" aria-label="Punkto World home"><span class="brand-orb"></span>punkto<span class="world-word">world</span></a><span class="edition">EXPLORATION / 001</span></header>
    <section class="intro"><p class="eyebrow">DENMARK · 55.6761° N / 12.5683° E</p><h1>Copenhagen<span>, alive.</span></h1><p>Small stories. Real places. A world to wander.</p></section>
    <div class="world-tools"><button id="home" title="Return to Copenhagen">⌖ <span>Copenhagen</span></button><button id="theme-toggle" aria-label="Light theme" aria-pressed="false"><span data-mode="dark">Dark</span> · <span data-mode="light">Light</span></button><span class="fixture-badge">${useFixtures ? 'Fixture world' : 'Live world'}</span></div>
    <p id="status" class="status" role="status">Opening the world…</p>
    <aside id="detail" class="detail" aria-label="Atom details" hidden tabindex="-1"><button id="close" class="close" aria-label="Close atom details">×</button><p class="eyebrow">A MESSAGE EXISTS HERE</p><p id="message" class="message"></p><div class="byline"><span id="avatar"></span><span id="identity"></span><time id="timestamp"></time></div><div id="location" class="location"></div></aside>
    <section class="timeline" aria-label="Time exploration"><div class="timeline-top"><div><p class="eyebrow">EXPLORE THROUGH TIME</p><span class="day" id="day"></span></div><output id="time" for="time-slider"></output></div><label class="sr-only" for="time-slider">Show messages posted up to this time, Copenhagen time</label><input id="time-slider" type="range" min="0" max="1000" value="1000" step="1"><div class="timeline-bottom"><span id="time-start"></span><span id="count" aria-live="polite"></span><span id="time-end"></span></div><details class="nearby"><summary>Explore visible messages</summary><div id="atom-list"></div></details></section>
    <p class="gesture-hint">Drag to wander · Scroll to explore · Right-drag to tilt & rotate · v1.0</p>`;
  const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const slider = el<HTMLInputElement>('time-slider');
  const day = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Copenhagen', day: 'numeric', month: 'long', year: 'numeric' });
  const shortDay = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Copenhagen', day: '2-digit', month: '2-digit' });
  const label = (t: number) => `${shortDay.format(t)} ${date.format(t)}`;
  const updateTime = () => {
    const to = Math.round(window.from + Number(slider.value) / Number(slider.max) * (window.to - window.from));
    el<HTMLOutputElement>('time').textContent = `${date.format(to)} CPH`;
    el('day').textContent = day.format(to);
    slider.setAttribute('aria-valuetext', `Messages through ${day.format(to)} ${date.format(to)} Copenhagen time`);
    return to;
  };
  const timeWindow = (next: TimeWindow) => {
    window = next;
    slider.max = useFixtures ? '17' : '1000';
    slider.value = slider.max;
    slider.disabled = window.from === window.to;
    el('day').textContent = day.format(window.from);
    el('time-start').textContent = label(window.from);
    el('time-end').textContent = label(window.to);
    updateTime();
  };
  timeWindow(window);
  slider.addEventListener('input', () => onTime(updateTime()));
  el('theme-toggle').addEventListener('click', onTheme);
  el('home').addEventListener('click', onHome);
  el('close').addEventListener('click', onClose);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') onClose(); });
  return {
    timeWindow,
    theme(theme: 'dark' | 'light') {
      el('theme-toggle').setAttribute('aria-pressed', String(theme === 'light'));
    },
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
