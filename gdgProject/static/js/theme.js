/**
 * CampusArena — Dark / Light Theme Toggle  [E9]
 *
 * Strategy:
 *   1. On page load, read saved preference from localStorage.
 *      If none, respect OS prefers-color-scheme.
 *   2. Apply the theme synchronously before paint via data-theme on <html>.
 *   3. On toggle, use View Transition API (document.startViewTransition) to
 *      animate a circular reveal from the button's click origin.
 *      Falls back to instant swap on unsupported browsers.
 */

(function () {
  var STORAGE_KEY = "campusarena-theme";
  var ROOT = document.documentElement;

  /* ── Helpers ─────────────────────────────────────────────── */
  function getSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function getSavedTheme() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (_) { return null; }
  }

  function saveTheme(theme) {
    try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
  }

  function applyTheme(theme) {
    ROOT.setAttribute("data-theme", theme);
    var label = document.getElementById("theme-label");
    if (label) label.textContent = theme === "dark" ? "Dark" : "Light";
    document.querySelectorAll("[data-theme-icon]").forEach(function (el) {
      el.textContent = theme === "dark" ? "☀" : "🌙";
      el.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    });
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#1a1a18" : "#534AB7");
  }

  /* ── Inject the one-time CSS for the transition ─────────── */
  function injectTransitionStyle() {
    if (document.getElementById("ca-theme-vt-style")) return;
    var s = document.createElement("style");
    s.id = "ca-theme-vt-style";
    s.textContent = [
      "::view-transition-old(root),",
      "::view-transition-new(root) {",
      "  animation: none;",
      "  mix-blend-mode: normal;",
      "}",
      /* New theme slides in as an expanding circle */
      "::view-transition-new(root) {",
      "  clip-path: var(--vt-clip-path-end, circle(0% at 50% 50%));",
      "  animation: ca-theme-reveal 750ms cubic-bezier(0.4, 0, 0.2, 1) forwards;",
      "}",
      "@keyframes ca-theme-reveal {",
      "  from { clip-path: var(--vt-clip-path-start, circle(0% at 50% 50%)); }",
      "  to   { clip-path: var(--vt-clip-path-end,   circle(150% at 50% 50%)); }",
      "}",
    ].join("\n");
    document.head.appendChild(s);
  }

  /* ── Main toggle ─────────────────────────────────────────── */
  function toggleTheme(event) {
    var current = ROOT.getAttribute("data-theme") || getSystemTheme();
    var next = current === "dark" ? "light" : "dark";
    saveTheme(next);

    /* Prefer View Transition API for the reveal animation */
    if (!document.startViewTransition) {
      applyTheme(next);      // instant fallback
      return;
    }

    injectTransitionStyle();

    /* Calculate the origin point (where the button is on screen) */
    var x = window.innerWidth / 2;
    var y = window.innerHeight / 2;
    if (event && event.currentTarget) {
      var rect = event.currentTarget.getBoundingClientRect();
      x = Math.round(rect.left + rect.width / 2);
      y = Math.round(rect.top  + rect.height / 2);
    }

    /* Diagonal = max possible radius to cover the full viewport */
    var dx = Math.max(x, window.innerWidth  - x);
    var dy = Math.max(y, window.innerHeight - y);
    var radius = Math.ceil(Math.hypot(dx, dy));

    ROOT.style.setProperty("--vt-clip-path-start", "circle(0px at " + x + "px " + y + "px)");
    ROOT.style.setProperty("--vt-clip-path-end",   "circle(" + radius + "px at " + x + "px " + y + "px)");

    var transition = document.startViewTransition(function () {
      applyTheme(next);
    });
    transition.ready.catch(function () { applyTheme(next); });
  }

  /* ── Bootstrap ───────────────────────────────────────────── */
  applyTheme(getSavedTheme() || getSystemTheme());

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

  window.addEventListener("storage", function (e) {
    if (e.key === STORAGE_KEY && e.newValue) applyTheme(e.newValue);
  });

  window.CampusArenaTheme = { toggle: toggleTheme, apply: applyTheme };
})();
