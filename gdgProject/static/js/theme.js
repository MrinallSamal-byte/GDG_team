/**
 * CampusArena — Dark / Light Theme Toggle  [E8]
 *
 * Strategy:
 *   1. On page load, read saved preference from localStorage.
 *      If none exists, respect the OS-level prefers-color-scheme.
 *   2. Apply the theme immediately (before paint) by setting
 *      data-theme="dark" | "light" on <html>.
 *   3. All colour tokens are CSS custom properties defined per theme;
 *      no runtime class-swapping on individual elements needed.
 *
 * Usage in any template:
 *   <script src="{% static 'js/theme.js' %}"></script>
 *   <button data-theme-toggle aria-label="Toggle theme">
 *     <span data-theme-icon></span>
 *   </button>
 *
 * The script is intentionally small and has zero dependencies.
 */

(function () {
  var STORAGE_KEY = "ca-theme";
  var ROOT = document.documentElement;

  function getSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (_) {}
  }

  function applyTheme(theme) {
    ROOT.setAttribute("data-theme", theme);
    // Update all toggle icons on the page
    document.querySelectorAll("[data-theme-icon]").forEach(function (el) {
      el.textContent = theme === "dark" ? "☀" : "🌙";
      el.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    });
    // Update <meta name="theme-color"> for PWA chrome
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", theme === "dark" ? "#1a1a18" : "#534AB7");
    }
  }

  function toggleTheme() {
    var current = ROOT.getAttribute("data-theme") || getSystemTheme();
    var next = current === "dark" ? "light" : "dark";
    saveTheme(next);
    applyTheme(next);
  }

  // --- Apply on first load (runs synchronously, before render) ---
  var initial = getSavedTheme() || getSystemTheme();
  applyTheme(initial);

  // --- Wire up toggle buttons after DOM is ready ---
  function wireButtons() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", toggleTheme);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireButtons);
  } else {
    wireButtons();
  }

  // --- Sync across tabs ---
  window.addEventListener("storage", function (e) {
    if (e.key === STORAGE_KEY && e.newValue) {
      applyTheme(e.newValue);
    }
  });

  // --- Expose globally for programmatic use ---
  window.CampusArenaTheme = { toggle: toggleTheme, apply: applyTheme };
})();
