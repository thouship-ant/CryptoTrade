var CACHE_NAME = 'offline-calculator';
var urlsToCache = [
  '/static/script.js',
  '/dashboard-crypto',
  '/crypto-wallet',
  '/crypto-orders',
  '/crypto-reports',
  '/configuration',
  '/plan-pricing',
  '/referral-page',
  '/faqs',
  '/assets/libs/gridjs/theme/mermaid.min.css',
  '/assets/libs/swiper/swiper-bundle.min.css',
  '/assets/css/bootstrap.min.css',
  '/assets/css/icons.min.css',
  '/assets/css/app.min.css',
  '/assets/css/custom.min.css',
  '/assets/images/favicon.ico',
  '/assets/images/offline.gif',
  '/assets/images/logo-light.png',
  '/assets/images/users/user-dummy-img.jpg',
  '/assets/images/187-suitcase-outline-edited.json',
  '/assets/js/layout.js',
  '/assets/libs/bootstrap/js/bootstrap.bundle.min.js',
  '/assets/libs/simplebar/simplebar.min.js',
  '/assets/libs/node-waves/waves.min.js',
  '/assets/libs/feather-icons/feather.min.js',
  '/assets/js/pages/plugins/lord-icon-2.1.0.js',
  '/assets/js/plugins.js',
  '/assets/libs/angular-1.8.2/angular.min.js',
  '/assets/libs/apexcharts/apexcharts.min.js',
  '/assets/libs/swiper/swiper-bundle.min.js',
  '/assets/libs/prismjs/prism.js',
  '/assets/libs/gridjs/gridjs.umd.js'
];
self.addEventListener('uninstall', function(event) {
  // install files needed offline
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('delete cache: ', urlsToCache[0]);
        return cache.delete(urlsToCache[0]);
      })
  );
});
