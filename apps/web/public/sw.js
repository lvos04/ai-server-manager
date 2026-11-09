/* Service worker van de Hub: alleen de app-schil offline (HTML-schil, JS/CSS, iconen) — NOOIT API-gegevens.
 * Gegevens (/api, /connector, /healthz, /readyz) gaan altijd naar het netwerk; offline zijn ze dus onbekend, nooit
 * een oude kopie die als actueel lijkt. Navigatie: netwerk eerst, daarna de bewaarde schil, anders /offline.html. */
const VERSION = new URL(self.location.href).searchParams.get("v") || "0";
const CACHE = `hub-schil-${VERSION}`;
const PRECACHE = ["/offline.html", "/manifest.webmanifest", "/icons/icon.svg", "/icons/icon-192.png"];
const NEVER = [/^\/api(\/|$)/, /^\/connector\//, /^\/healthz$/, /^\/readyz$/];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("hub-schil-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER.some((re) => re.test(url.pathname))) return; // altijd netwerk, nooit cache

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(url.pathname, copy));
          }
          return res;
        })
        .catch(async () => (await caches.match(url.pathname)) || (await caches.match("/offline.html"))),
    );
    return;
  }

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          }),
      ),
    );
  }
});
