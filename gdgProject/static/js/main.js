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

    /* ---------- Tabs (with ARIA) ---------- */
    document.querySelectorAll('.tab-bar').forEach(bar => {
        const btns = bar.querySelectorAll('.tab-btn');
        const container = bar.closest('.tab-container') || bar.parentElement;
        const panels = container.querySelectorAll('.tab-panel');

        btns.forEach(btn => {
            btn.addEventListener('click', () => {
                btns.forEach(b => {
                    b.classList.remove('active');
                    b.setAttribute('aria-selected', 'false');
                });
                panels.forEach(p => {
                    p.classList.remove('active');
                    p.setAttribute('aria-hidden', 'true');
                });
                btn.classList.add('active');
                btn.setAttribute('aria-selected', 'true');
                const target = container.querySelector('#' + btn.dataset.tab);
                if (target) {
                    target.classList.add('active');
                    target.setAttribute('aria-hidden', 'false');
                }
            });
        });
    });

    /* ---------- FAQ accordion (with ARIA) ---------- */
    document.querySelectorAll('.faq-toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const item = toggle.closest('.faq-item');
            if (!item) return;
            const wasOpen = item.classList.contains('open');
            const parent = item.parentElement;
            if (parent) {
                parent.querySelectorAll('.faq-item.open').forEach(i => {
                    i.classList.remove('open');
                    const btn = i.querySelector('.faq-toggle');
                    if (btn) btn.setAttribute('aria-expanded', 'false');
                });
            }
            if (!wasOpen) {
                item.classList.add('open');
                toggle.setAttribute('aria-expanded', 'true');
            }
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
            // Sync active chips to hidden input if present
            const container = chip.closest('form');
            if (container) {
                const hidden = container.querySelector('input[name="skills"]');
                if (hidden) {
                    const active = container.querySelectorAll('.chip-toggle .chip.active');
                    hidden.value = Array.from(active).map(c => c.dataset.skill || c.textContent.trim()).join(',');
                }
            }
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

    /* ---------- User dropdown menu ---------- */
    const userMenuBtn = document.getElementById('user-menu-btn');
    const userDropdown = document.getElementById('user-dropdown');

    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = userDropdown.classList.toggle('open');
            userMenuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        document.addEventListener('click', (e) => {
            if (!userDropdown.contains(e.target) && e.target !== userMenuBtn) {
                userDropdown.classList.remove('open');
                userMenuBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* ---------- Alert dismiss ---------- */
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-8px)';
                setTimeout(() => alert.remove(), 200);
            }
        });
    });

    /* ---------- Password visibility toggle ---------- */
    document.querySelectorAll('input[type="password"]').forEach(inp => {
        const wrapper = inp.closest('.form-group, .form-field');
        if (!wrapper) return;
        wrapper.style.position = 'relative';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'password-toggle';
        btn.setAttribute('aria-label', 'Toggle password visibility');
        btn.innerHTML = '<i data-lucide="eye"></i>';
        wrapper.appendChild(btn);

        btn.addEventListener('click', () => {
            const isPassword = inp.type === 'password';
            inp.type = isPassword ? 'text' : 'password';
            btn.innerHTML = isPassword ? '<i data-lucide="eye-off"></i>' : '<i data-lucide="eye"></i>';
            if (window.lucide) lucide.createIcons();
        });
    });

    /* ---------- Create Event Form Logic ---------- */
    const createEventForm = document.getElementById('create-event-form');
    if (createEventForm) {
        const participationSelect = createEventForm.querySelector('select[name="participation_type"]');
        const minTeamField = createEventForm.querySelector('input[name="min_team_size"]');
        const maxTeamField = createEventForm.querySelector('input[name="max_team_size"]');

        if (participationSelect && minTeamField && maxTeamField) {
            function updateTeamFields() {
                const val = participationSelect.value;
                const minWrapper = minTeamField.closest('.form-field');
                const maxWrapper = maxTeamField.closest('.form-field');
                if (val === 'Solo') {
                    if (minWrapper) minWrapper.style.display = 'none';
                    if (maxWrapper) maxWrapper.style.display = 'none';
                    minTeamField.required = false;
                    maxTeamField.required = false;
                } else {
                    if (minWrapper) minWrapper.style.display = 'block';
                    if (maxWrapper) maxWrapper.style.display = 'block';
                    minTeamField.required = true;
                    maxTeamField.required = true;
                }
            }
            participationSelect.addEventListener('change', updateTeamFields);
            updateTeamFields(); // Initial call
        }

        // Date logic
        const startDateInput = createEventForm.querySelector('input[name="start_date"]');
        const endDateInput = createEventForm.querySelector('input[name="end_date"]');
        if (startDateInput && endDateInput) {
            startDateInput.addEventListener('change', () => {
                endDateInput.min = startDateInput.value;
            });
            endDateInput.addEventListener('change', () => {
                if (startDateInput.value && endDateInput.value < startDateInput.value) {
                    endDateInput.value = startDateInput.value;
                }
            });
        }
    }

    /* ---------- Re-init lucide icons (for dynamic content) ---------- */
    if (window.lucide) lucide.createIcons();
});
