/* Sky lab: a floating panel in preview builds only (build.py --preview), for trying the Now sky at any time of day,
   haze level, weather and theme. It swaps the page's skyTime, skyWeather and now() for its own settings.
   ?sky=HH:MM,pm,weather,theme,extras opens with those settings, e.g. ?sky=18:40,180,live,light,skyline */
(() => {
  const L = {min:null, pm:null, wx:null, theme:'auto', play:false};
  const sgNow = () => { const d = new Date(Date.now() + 8 * 3600e3); return d.getUTCHours() * 60 + d.getUTCMinutes(); };
  const at = m => { const d = new Date(Date.now() + 8 * 3600e3); return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) + (m - 480) * 60e3); };
  const clock = m => { const h = Math.floor(m / 60) % 24, mm = String(Math.floor(m % 60)).padStart(2, '0'); return `${h % 12 || 12}:${mm} ${h < 12 ? 'am' : 'pm'}`; };
  window.skyTime = () => L.min == null ? new Date() : at(L.min);
  const liveWx = window.skyWeather;
  window.skyWeather = () => L.wx || liveWx();
  const realNow = window.now;
  window.now = r => { const n = realNow(r); return L.pm == null ? n : {...n, pm:L.pm, b:PM[pmIdx(L.pm)]}; };

  const q = (new URLSearchParams(location.search).get('sky') || '').split(',');
  if (q[0]){ const [h, m] = q[0].split(':'); L.min = +h * 60 + (+m || 0); }
  if (q[1]) L.pm = +q[1];
  if (q[2] && q[2] !== 'live') L.wx = q[2];
  if (q[3] && q[3] !== 'auto'){ L.theme = q[3]; document.documentElement.dataset.theme = q[3]; }
  if (q.includes('skyline')) SKY_OPTS.skyline = true;
  if (q.includes('norays')) SKY_OPTS.rays = false;
  const panelOff = q.includes('nolab');

  const css = `
  .lab-fab{position:fixed;right:12px;bottom:calc(84px + env(safe-area-inset-bottom,0px));z-index:30;border:0;border-radius:999px;padding:9px 14px 9px 11px;
    font:800 13px var(--body);display:flex;gap:6px;align-items:center;background:#12202B;color:#F3EEE6;box-shadow:0 10px 26px -10px rgba(0,0,0,.6)}
  .lab-fab i{width:14px;height:14px;border-radius:50%;background:radial-gradient(circle at 50% 35%,#FFD9A0,#FF8A3D 60%,rgba(255,138,61,.2))}
  .lab{position:fixed;right:12px;bottom:calc(84px + env(safe-area-inset-bottom,0px));z-index:31;width:min(360px,calc(100vw - 24px));max-height:calc(100% - 120px);overflow:auto;
    background:rgba(18,32,43,.94);color:#F3EEE6;border-radius:18px;padding:12px 14px 14px;font:500 12.5px/1.35 var(--body);box-shadow:0 24px 60px -20px rgba(0,0,0,.7);
    -webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px)}
  @media (min-width:960px){.lab-fab,.lab{bottom:20px;right:20px}}
  .lab h5{margin:0;font:800 14px var(--display);display:flex;align-items:center;gap:8px}
  .lab h5 small{font:600 11px var(--body);opacity:.6;margin-right:auto}
  .lab h5 button{border:0;background:rgba(255,255,255,.1);color:inherit;border-radius:50%;width:26px;height:26px;font-size:15px;line-height:1}
  .lab .k{font-size:10.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;opacity:.6;margin:11px 0 5px;display:flex;justify-content:space-between}
  .lab .k span{text-transform:none;letter-spacing:0;font-weight:700;opacity:1;font-size:12px}
  .lab .lseg{display:flex;flex-wrap:wrap;gap:4px}
  .lab .lseg button{flex:1 1 auto;border:0;border-radius:9px;background:rgba(255,255,255,.08);color:inherit;font:700 12px var(--body);padding:6px 7px}
  .lab .lseg button[aria-pressed="true"]{background:#F3EEE6;color:#12202B}
  .lab input[type=range]{width:100%;accent-color:#FF9A4D;margin:2px 0 4px}
  .lab .row2{display:flex;gap:6px;align-items:center}
  .lab .row2 input{flex:1}
  .lab .row2 button{border:0;border-radius:9px;background:rgba(255,255,255,.12);color:inherit;font:800 12px var(--body);padding:6px 10px;white-space:nowrap}
  .lab .info{margin-top:10px;font-size:11.5px;opacity:.7}
  .lab .note{font-size:11px;opacity:.6;margin-top:4px}`;
  document.head.append(Object.assign(document.createElement('style'), {textContent:css}));

  const TIMES = [['Sunrise', 6 * 60 + 58], ['Morning', 9 * 60 + 30], ['Noon', 13 * 60], ['Golden', 18 * 60 + 25], ['Dusk', 19 * 60 + 8], ['Night', 22 * 60 + 30]];
  const AIR = [['Live', null], ['Clear', 12], ['Normal', 45], ['Elevated', 110], ['High', 200], ['Very high', 300]];
  const WXS = [['Live', null], ['Fair', 'fair'], ['Partly', 'partly'], ['Cloudy', 'cloudy'], ['Rain', 'rain'], ['Storm', 'storm']];
  const THEME = [['Auto', 'auto'], ['Light', 'light'], ['Dark', 'dark']];
  const fab = Object.assign(document.createElement('button'), {className:'lab-fab', innerHTML:'<i></i>Sky lab'});
  const box = Object.assign(document.createElement('div'), {className:'lab', hidden:true});
  document.body.append(fab, box);
  const seg = (name, list, cur) => `<div class="lseg" data-g="${name}">${list.map(([l, v]) => `<button data-v="${v}" aria-pressed="${String(v) === String(cur)}">${l}</button>`).join('')}</div>`;
  function info(){
    const s = skyAt(now(P.region).pm), m = s.moon, k = (1 - Math.cos(2 * Math.PI * m.p)) / 2;
    const part = s.sun.alt > 20 ? 'day' : s.sun.alt > 0 ? 'golden hour' : s.sun.alt > -6 ? 'twilight' : 'night';
    return `Sun ${s.sun.alt.toFixed(0)}° · ${part} · ${s.wx}${L.wx ? '' : ' (live)'} · moon ${Math.round(k * 100)}% lit${m.alt > 0 ? ', up' : ''} · ${s.lightSky ? 'dark' : 'light'} text`;
  }
  function draw(){
    const m = L.min == null ? sgNow() : L.min;
    box.innerHTML = `<h5>Sky lab <small>preview only · not on the site</small><button data-x aria-label="Close">×</button></h5>
      <div class="k">Time in Singapore <span id="lab-t">${clock(m)}${L.min == null ? ' · live' : ''}</span></div>
      <div class="row2"><input type="range" min="0" max="1439" value="${Math.round(m)}" id="lab-r"><button data-now>Now</button><button data-play>${L.play ? '❚❚' : '▶ Day'}</button></div>
      ${seg('t', TIMES, L.min)}
      <div class="k">Air (PM2.5)</div>${seg('pm', AIR, L.pm)}
      <div class="k">Weather <span style="opacity:.6;font-weight:600">NEA 2-hr forecast${S.wx ? '' : ' · unavailable here'}</span></div>${seg('wx', WXS, L.wx)}
      <div class="k">Theme</div>${seg('th', THEME, L.theme)}
      <div class="k">Extras</div>${seg('x', [['Sun rays', 'rays'], ['Skyline', 'skyline']].map(([l, v]) => [l + (SKY_OPTS[v] ? ' ✓' : ''), v]), '')}
      <div class="info" id="lab-i">${info()}</div>`;
    box.querySelectorAll('[data-g="x"] button').forEach(b => b.setAttribute('aria-pressed', SKY_OPTS[b.dataset.v]));
  }
  const rerender = () => { render(); draw(); };
  fab.onclick = () => { box.hidden = false; fab.hidden = true; draw(); };
  box.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.hasAttribute('data-x')){ box.hidden = true; fab.hidden = false; return; }
    if (b.hasAttribute('data-now')){ L.min = null; L.play = false; return rerender(); }
    if (b.hasAttribute('data-play')){ L.play = !L.play; if (L.play && L.min == null) L.min = sgNow(); if (L.play){ lastTick = 0; tick(); } return draw(); }
    const g = b.parentElement.dataset.g, v = b.dataset.v;
    if (g === 't'){ L.min = +v; L.play = false; }
    if (g === 'pm') L.pm = v === 'null' ? null : +v;
    if (g === 'wx') L.wx = v === 'null' ? null : v;
    if (g === 'th'){ L.theme = v; if (v === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = v; return draw(); }   // the page re-renders itself on a theme change
    if (g === 'x') SKY_OPTS[v] = !SKY_OPTS[v];
    rerender();
  });
  box.addEventListener('input', e => {
    if (e.target.id !== 'lab-r') return;
    L.min = +e.target.value; L.play = false;
    box.querySelector('#lab-t').textContent = clock(L.min);
    box.querySelector('[data-play]').textContent = '▶ Day';
    box.querySelector('#lab-i').textContent = info();
    box.querySelectorAll('[data-g="t"] button').forEach(b => b.setAttribute('aria-pressed', 'false'));
  });
  // ▶ Day: a whole day in about 30 seconds
  let lastTick = 0;
  function tick(ts){
    if (!L.play) return;
    if (ts && lastTick){ L.min = (L.min + (ts - lastTick) / 1000 * 48) % 1440;
      const r = box.querySelector('#lab-r'); if (r){ r.value = Math.round(L.min); box.querySelector('#lab-t').textContent = clock(L.min); box.querySelector('#lab-i').textContent = info(); } }
    lastTick = ts || 0;
    requestAnimationFrame(tick);
  }
  if (q[0] || q[1] || q[2]) render();
  // open on wide screens; on a phone it would cover the sky, so it starts as a button
  if (panelOff) fab.hidden = true; else if (!q[0] && innerWidth >= 960){ box.hidden = false; fab.hidden = true; draw(); }
})();
