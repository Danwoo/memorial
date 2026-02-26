const CACHE_NAME = 'memoir-v2';
const OFFLINE_URL = '/offline.html';

// ─── Install: offline.html만 프리캐시 ─────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.add(OFFLINE_URL))
  );
  self.skipWaiting();
});

// ─── Activate: 이전 버전 캐시 전체 삭제 ──────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ─── Fetch: navigation만 인터셉트 (오프라인 폴백) ─────────
// JS/CSS는 Vite가 content-hash 파일명을 사용하므로 브라우저 HTTP 캐시로 충분.
// SW가 script/style을 캐싱하면 새 배포 후 구 번들이 반환되는 문제 발생.
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL))
    );
  }
});

// ─── Push 알림 ──────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = { title: 'Memoir', body: '새 알림이 있습니다', url: '/' };
  try {
    data = event.data.json();
  } catch {
    // 기본값 사용
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/favicon.png',
      badge: '/favicon.png',
      data: { url: data.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});
