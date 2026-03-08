const root = document.documentElement;
const toggle = document.getElementById('theme-toggle');
const label = document.getElementById('theme-label');

function setTheme(theme, animate) {
    if (animate) {
        document.body.classList.add('theme-transitioning');
    }
    root.setAttribute('data-theme', theme);
    localStorage.setItem('campusarena-theme', theme);
    if (label) {
        label.textContent = theme === 'dark' ? 'Dark' : 'Light';
    }
    if (toggle) {
        toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    }
    if (animate) {
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
        }, 450);
    }
}

function initTheme() {
    const saved = localStorage.getItem('campusarena-theme') || root.getAttribute('data-theme') || 'dark';
    setTheme(saved, false);
}

if (toggle) {
    toggle.addEventListener('click', () => {
        const current = root.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        setTheme(next, true);
    });
}

initTheme();
