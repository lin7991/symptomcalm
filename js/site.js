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
