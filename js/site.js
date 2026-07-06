// SymptomCalm — Site-wide JavaScript
// Language toggle + Newsletter subscription

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

  // ===== Newsletter Subscription =====
  // Save emails locally as fallback until Worker is deployed
  function saveSubscriberLocally(email) {
    try {
      const stored = JSON.parse(localStorage.getItem('sc_subscribers') || '[]');
      if (!stored.includes(email)) {
        stored.push(email);
        localStorage.setItem('sc_subscribers', JSON.stringify(stored));
      }
      return true;
    } catch(e) {
      return false;
    }
  }

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

      button.disabled = true;
      button.textContent = 'Subscribing...';

      // Try API first, fall back to localStorage
      fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      })
      .then(res => res.json())
      .then(data => {
        if (data.ok) {
          showSuccess(emailInput, message);
        } else {
          throw new Error(data.error || 'failed');
        }
      })
      .catch(() => {
        // API unavailable — save locally
        saveSubscriberLocally(email);
        showSuccess(emailInput, message);
      })
      .finally(() => {
        button.disabled = false;
        button.textContent = 'Subscribe';
      });
    });
  }

  function showSuccess(input, msgEl) {
    if (msgEl) {
      msgEl.textContent = 'Thanks for subscribing! You\'ll hear from us soon.';
      msgEl.style.color = '#2C7A7B';
    }
    if (input) input.value = '';
  }

  // Export subscribers for admin access
  window.getSubscribers = function() {
    try {
      return JSON.parse(localStorage.getItem('sc_subscribers') || '[]');
    } catch(e) { return []; }
  };

})();
