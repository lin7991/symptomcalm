// Normalize GitHub Pages' duplicate /index.html URL variant to the directory URL.
// GitHub Pages serves both with HTTP 200; canonical tags alone may not consolidate
// every historical URL, so send browsers and Google-rendered sessions to the one URL.
(function() {
  const path = window.location.pathname;
  if (/\/index\.html$/i.test(path)) {
    const canonicalPath = path.slice(0, -'index.html'.length) || '/';
    window.location.replace(canonicalPath + window.location.search + window.location.hash);
  }
})();

// SymptomCalm — Language Toggle
// Works both EN→ZH and ZH→EN

(function() {
  'use strict';

  const langToggle = document.getElementById('lang-toggle');
  if (!langToggle) return;

  langToggle.addEventListener('click', function() {
    const path = window.location.pathname;

    if (path.startsWith('/zh/')) {
      // Currently on Chinese page → switch to English
      const enPath = path.replace('/zh', '') || '/';
      window.location.href = enPath;
    } else {
      // Currently on English page → switch to Chinese
      const zhPath = '/zh' + (path.endsWith('/') ? path : path + '/');
      // Check if Chinese version exists, fallback to /zh/
      fetch(zhPath, { method: 'HEAD' })
        .then(res => {
          window.location.href = res.ok ? zhPath : '/zh/';
        })
        .catch(() => {
          window.location.href = '/zh/';
        });
    }
  });

})();
