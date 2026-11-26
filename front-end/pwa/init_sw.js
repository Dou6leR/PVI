// PWA disabled: unregister any active Service Workers and clear Cache Storage
if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
        for (const registration of registrations) {
            registration.unregister();
        }
    });
}

if ("caches" in window) {
    caches.keys().then((names) => {
        for (const name of names) {
            caches.delete(name);
        }
    });
}
