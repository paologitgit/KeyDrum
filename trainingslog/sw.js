// Trainingslog – Service Worker: hält die App-Dateien für den Offline-Betrieb bereit.
// Daten laufen nicht hier durch: api.php wird nie zwischengespeichert.
const CACHE = 'trainingslog-v1';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', './index.html'])).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || /\/(api|check)\.php$/.test(url.pathname)) return;
  // Zuerst aus dem Netz (damit Updates ankommen), nach 4 s oder ohne Netz aus dem Zwischenspeicher
  e.respondWith(new Promise(resolve => {
    let done = false;
    const fromCache = () => caches.match(e.request, { ignoreSearch: true })
      .then(r => r || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined))
      .then(r => { if (!done && r) { done = true; resolve(r); } return r; });
    const timer = setTimeout(fromCache, 4000);
    fetch(e.request).then(res => {
      clearTimeout(timer);
      if (res.ok || res.type === 'opaque') { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      if (!done) { done = true; resolve(res); }
    }).catch(() => {
      clearTimeout(timer);
      fromCache().then(r => { if (!done) { done = true; resolve(r || Response.error()); } });
    });
  }));
});
