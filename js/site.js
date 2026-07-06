// SymptomCalm — Site-wide JavaScript
// Language toggle + Newsletter subscription

(function() {
  'use strict';

  // ===== Language Toggle =====
  const langToggle = document.getElementById('lang-toggle');
  if (langToggle) {
    langToggle.addEventListener('click', function() {
      // Detect current path and redirect to Chinese version
      const path = window.location.pathname;
      const zhPath = '/zh' + path;
      // Check if Chinese version exists
      fetch(zhPath, { method: 'HEAD' })
        .then(res => {
          if (res.ok) {
            window.location.href = zhPath;
          } else {
            // Fallback: go to Chinese homepage
            window.location.href = '/zh/';
          }
        })
        .catch(() => {
          window.location.href = '/zh/';
        });
    });
  }

  // ===== Newsletter Subscription =====
  const newsletterForm = document.getElementById('newsletter-form');
  if (newsletterForm) {
    newsletterForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const emailInput = document.getElementById('newsletter-email');
      const button = newsletterForm.querySelector('button');
      const message = document.getElementById('newsletter-message');
      const email = emailInput ? emailInput.value.trim() : '';

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        if (message) {
          message.textContent = 'Please enter a valid email address.';
          message.style.color = '#e53e3e';
        }
        return;
      }

      // Disable button during request
      button.disabled = true;
      button.textContent = 'Subscribing...';

      fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      })
      .then(res => res.json())
      .then(data => {
        if (data.ok) {
          if (message) {
            message.textContent = 'Thanks for subscribing! Check your inbox for confirmation.';
            message.style.color = '#2C7A7B';
          }
          if (emailInput) emailInput.value = '';
        } else {
          throw new Error(data.error || 'Subscription failed');
        }
      })
      .catch(err => {
        if (message) {
          message.textContent = 'Something went wrong. Please try again later.';
          message.style.color = '#e53e3e';
        }
      })
      .finally(() => {
        button.disabled = false;
        button.textContent = 'Subscribe';
      });
    });
  }

})();
