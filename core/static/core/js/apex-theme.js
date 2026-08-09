/* ==========================================================================
   Apex Theme — light/dark toggle with persistence
   Loaded after the body so the no-flash inline script in <head> has already
   set the initial data-theme attribute.
   ========================================================================== */
(function () {
  'use strict';

  function getTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
    updateIcons(theme);
    // Notify any listeners (e.g. charts) that the theme changed.
    document.dispatchEvent(new CustomEvent('apex:themechange', { detail: { theme: theme } }));
  }

  function toggleTheme() {
    setTheme(getTheme() === 'light' ? 'dark' : 'light');
  }

  function updateIcons(theme) {
    // Bootstrap-icons based toggles (id="themeIcon")
    var bsIcon = document.getElementById('themeIcon');
    if (bsIcon) {
      bsIcon.className = theme === 'light' ? 'bi bi-moon' : 'bi bi-brightness-high';
    }
    // Lucide based toggles (data-apex-theme-icon)
    document.querySelectorAll('[data-apex-theme-icon]').forEach(function (el) {
      el.setAttribute('data-lucide', theme === 'light' ? 'moon' : 'sun');
    });
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  // Bind every element marked as a toggle.
  function bindToggles() {
    document.querySelectorAll('[data-apex-toggle]').forEach(function (btn) {
      if (btn.__apexBound) return;
      btn.__apexBound = true;
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        toggleTheme();
      });
    });
  }

  // Expose globally (back-compat with existing onclick="toggleTheme()" calls).
  window.toggleTheme = toggleTheme;
  window.setApexTheme = setTheme;
  window.getApexTheme = getTheme;

  function init() {
    // Ensure the stored theme wins over any hard-coded attribute.
    var stored;
    try { stored = localStorage.getItem('theme'); } catch (e) {}
    if (stored === 'light' || stored === 'dark') {
      document.documentElement.setAttribute('data-theme', stored);
    }
    updateIcons(getTheme());
    bindToggles();
  }

  // Script lives at the end of <body>, so the DOM is usually already parsed.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-bind toggles for any late-injected markup (e.g. AJAX partials).
  document.addEventListener('apex:bindtoggles', bindToggles);
})();
