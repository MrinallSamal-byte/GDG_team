/* ========================================================================
   CampusArena — Interactive Features
   ======================================================================== */

document.addEventListener('DOMContentLoaded', () => {

    /* ---------- Header scroll shadow ---------- */
    const header = document.querySelector('.site-header');
    if (header) {
        const onScroll = () => {
            header.classList.toggle('scrolled', window.scrollY > 10);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    /* ---------- Mobile menu ---------- */
    const mobileToggle = document.getElementById('mobile-toggle');
    const mobileNav = document.getElementById('mobile-nav');
    const navOverlay = document.getElementById('nav-overlay');
    const mobileClose = document.getElementById('mobile-close');

    function openMobile() {
        if (mobileNav) mobileNav.classList.add('open');
        if (navOverlay) navOverlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeMobile() {
        if (mobileNav) mobileNav.classList.remove('open');
        if (navOverlay) navOverlay.classList.remove('open');
        document.body.style.overflow = '';
    }

    if (mobileToggle) mobileToggle.addEventListener('click', openMobile);
    if (mobileClose) mobileClose.addEventListener('click', closeMobile);
    if (navOverlay) navOverlay.addEventListener('click', closeMobile);

    /* ---------- Scroll reveal ---------- */
    const revealEls = document.querySelectorAll('.reveal');
    if (revealEls.length && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
        revealEls.forEach(el => observer.observe(el));
    } else {
        revealEls.forEach(el => el.classList.add('revealed'));
    }

    /* ---------- Tabs ---------- */
    document.querySelectorAll('.tab-bar').forEach(bar => {
        const btns = bar.querySelectorAll('.tab-btn');
        const container = bar.closest('.tab-container') || bar.parentElement;
        const panels = container.querySelectorAll('.tab-panel');

        btns.forEach(btn => {
            btn.addEventListener('click', () => {
                btns.forEach(b => b.classList.remove('active'));
                panels.forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
                const target = container.querySelector('#' + btn.dataset.tab);
                if (target) target.classList.add('active');
            });
        });
    });

    /* ---------- FAQ accordion ---------- */
    document.querySelectorAll('.faq-toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const item = toggle.closest('.faq-item');
            if (!item) return;
            const wasOpen = item.classList.contains('open');
            // close all sibling FAQs
            const parent = item.parentElement;
            if (parent) {
                parent.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));
            }
            if (!wasOpen) item.classList.add('open');
        });
    });

    /* ---------- Countdown timer ---------- */
    document.querySelectorAll('[data-deadline]').forEach(el => {
        function updateCountdown() {
            const deadline = new Date(el.dataset.deadline).getTime();
            const now = Date.now();
            const diff = Math.max(0, deadline - now);

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const secs = Math.floor((diff % (1000 * 60)) / 1000);

            const dEl = el.querySelector('[data-days]');
            const hEl = el.querySelector('[data-hours]');
            const mEl = el.querySelector('[data-mins]');
            const sEl = el.querySelector('[data-secs]');

            if (dEl) dEl.textContent = String(days).padStart(2, '0');
            if (hEl) hEl.textContent = String(hours).padStart(2, '0');
            if (mEl) mEl.textContent = String(mins).padStart(2, '0');
            if (sEl) sEl.textContent = String(secs).padStart(2, '0');
        }

        updateCountdown();
        setInterval(updateCountdown, 1000);
    });

    /* ---------- Skill chip toggle ---------- */
    document.querySelectorAll('.chip-toggle .chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('active');
        });
    });

    /* ---------- OTP auto-advance ---------- */
    document.querySelectorAll('.otp-grid').forEach(grid => {
        const inputs = grid.querySelectorAll('input');
        inputs.forEach((inp, idx) => {
            inp.addEventListener('input', () => {
                if (inp.value.length >= 1 && idx < inputs.length - 1) {
                    inputs[idx + 1].focus();
                }
            });
            inp.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && inp.value === '' && idx > 0) {
                    inputs[idx - 1].focus();
                }
            });
        });
    });

    /* ---------- Animated counters ---------- */
    document.querySelectorAll('[data-counter]').forEach(el => {
        const target = parseInt(el.textContent.replace(/[^0-9]/g, ''), 10);
        if (isNaN(target)) return;
        const suffix = el.textContent.replace(/[0-9,]/g, '');
        let current = 0;
        const duration = 1200;
        const steps = 40;
        const increment = target / steps;
        const stepMs = duration / steps;

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                observer.unobserve(el);
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= target) {
                        current = target;
                        clearInterval(timer);
                    }
                    el.textContent = Math.floor(current).toLocaleString() + suffix;
                }, stepMs);
            }
        }, { threshold: 0.5 });

        observer.observe(el);
    });

    /* ---------- Filter chips ---------- */
    document.querySelectorAll('.filters').forEach(filterRow => {
        filterRow.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                filterRow.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
            });
        });
    });
});
