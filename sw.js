// Haze Status service worker. It does one thing: if the visitor is offline, opening the app shows the last copy of
// the page (which then says it can't reach NEA) instead of the browser's error page. Pages always come from the
// network first, so a deploy shows up at once. Readings are never cached; they are always fetched live from NEA.
const CACHE = 'haze-shell-v1';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.add('/')).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.mode !== 'navigate' || new URL(req.url).origin !== location.origin) return;   // everything else goes straight to the network
  e.respondWith(fetch(req).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put('/', copy)); }
    return res;
  }).catch(() => caches.match('/')));
});
