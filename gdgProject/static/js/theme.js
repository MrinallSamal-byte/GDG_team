const root = document.documentElement;
const toggle = document.getElementById('theme-toggle');
const label = document.getElementById('theme-label');

function setTheme(theme) {
    root.setAttribute('data-theme', theme);
    localStorage.setItem('campusarena-theme', theme);
    if (label) {
        label.textContent = theme === 'dark' ? 'Dark' : 'Light';
    }
    if (toggle) {
        toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    }
}

function initTheme() {
    const saved = localStorage.getItem('campusarena-theme') || root.getAttribute('data-theme') || 'light';
    setTheme(saved);
}

if (toggle) {
    toggle.addEventListener('click', () => {
        const current = root.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        setTheme(next);
    });
}

initTheme();
