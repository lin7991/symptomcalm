// SymptomCalm — Site-wide JavaScript
// Language toggle only

(function() {
  'use strict';

  // ===== Language Toggle =====
  const langToggle = document.getElementById('lang-toggle');
  if (langToggle) {
    langToggle.addEventListener('click', function() {
      const path = window.location.pathname;
      const zhPath = '/zh' + path;
      fetch(zhPath, { method: 'HEAD' })
        .then(res => {
          window.location.href = res.ok ? zhPath : '/zh/';
        })
        .catch(() => {
          window.location.href = '/zh/';
        });
    });
  }

})();
