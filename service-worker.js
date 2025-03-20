const CACHE_NAME = "pwa-cache-v1";
const ASSETS = [
    "/PVI/students_page/students.html",
    "/PVI/students_page/students.css",
    "/PVI/students_page/students.js",
    "/PVI/dashboard_page/dashboard.html",
    //"/PVI/dashboard_page/dashboard.css",
    //"/PVI/dashboard_page/dashboard.js",
    "/PVI/messages_page/messages.html",
    //"/PVI/messages_page/messages.css",
    //"/PVI/messages_page/messages.js",
    "/PVI/tasks_page/tasks.html",
    //"/PVI/tasks_page/tasks.css",
    //"/PVI/tasks_page/tasks.js",
    "/PVI/index.html",
    "/PVI/main.css",
    "/PVI/app.js",
    "/PVI/service-worker.js",
    "/PVI/pwa/init_sw.js",
    "/PVI/pwa/manifest.json",
    "/PVI/src/bell.png",
    "/PVI/icons/user.png"
];

// Встановлення Service Worker та кешування файлів
self.addEventListener("install", (event) => {
    event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
    return cache.addAll(ASSETS);
    })
);
});

// Перехоплення запитів і завантаження з кешу
self.addEventListener("fetch", (event) => {
    event.respondWith(
    caches.match(event.request).then((response) => {
    return response || fetch(event.request);
    })
);
});

// Оновлення Service Worker і видалення старого кешу
self.addEventListener("activate", (event) => {
    event.waitUntil(
    caches
    .keys()
    .then((keys) => {
        return Promise.all(
            keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        );
    })
    .then(() => {
        return self.clients.claim(); // Підключаємо новий SW до всіх вкладок
    })
);
});