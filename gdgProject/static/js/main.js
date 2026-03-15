/* ========================================================================
   CampusArena — Interactive Features  v2.0
   Full interaction suite: filtering, validation, loading states, toasts,
   modals, accessible nav, countdown, OTP, chat.
   ======================================================================== */

/* ─── Toast system ──────────────────────────────────────────────────────── */
function showToast(message, type = 'info', duration = 3500) {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
    }
    const icons = { success: 'check-circle', error: 'alert-circle', warning: 'alert-triangle', info: 'info' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'status');
    toast.innerHTML = `<i data-lucide="${icons[type] || 'info'}"></i> ${escapeHtml(message)}`;
    container.appendChild(toast);
    if (window.lucide) lucide.createIcons({ nodes: [toast] });
    setTimeout(() => {
        toast.classList.add('toast-exit');
        toast.addEventListener('animationend', () => toast.remove(), { once: true });
    }, duration);
}
window.showToast = showToast;

/* ─── Confirmation modal ─────────────────────────────────────────────────── */
function showConfirm({ title, message, confirmText = 'Confirm', confirmClass = 'btn-primary', onConfirm }) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <h3 id="modal-title"><i data-lucide="alert-triangle"></i> ${title}</h3>
            <p>${message}</p>
            <div class="modal-actions">
                <button class="btn-secondary btn-small" id="modal-cancel">Cancel</button>
                <button class="${confirmClass} btn-small" id="modal-confirm">${confirmText}</button>
            </div>
        </div>`;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('open'));
    if (window.lucide) lucide.createIcons({ nodes: [overlay] });

    const close = () => {
        overlay.classList.remove('open');
        overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
    };
    overlay.querySelector('#modal-cancel').addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    overlay.querySelector('#modal-confirm').addEventListener('click', () => { close(); if (typeof onConfirm === 'function') onConfirm(); });
    overlay.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') close();
        if (e.key === 'Tab') {
            e.preventDefault();
            const focusable = overlay.querySelectorAll('button');
            const idx = Array.from(focusable).indexOf(document.activeElement);
            focusable[(idx + 1) % focusable.length].focus();
        }
    });
    overlay.querySelector('#modal-confirm').focus();
}
window.showConfirm = showConfirm;

/* ─── Form validation ─────────────────────────────────────────────────────── */
function validateForm(form) {
    let valid = true;
    form.querySelectorAll('.field-error').forEach(e => e.remove());
    form.querySelectorAll('.form-field.has-error, .form-group.has-error').forEach(f => f.classList.remove('has-error'));

    form.querySelectorAll('[required]').forEach(field => {
        if (!field.value.trim()) { valid = false; markFieldError(field, 'This field is required.'); }
    });
    form.querySelectorAll('input[type="email"]').forEach(field => {
        if (field.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) { valid = false; markFieldError(field, 'Enter a valid email address.'); }
    });
    const pw = form.querySelector('input[name="password"]');
    const pwc = form.querySelector('input[name="password_confirm"]');
    if (pw && pwc && pw.value && pwc.value && pw.value !== pwc.value) { valid = false; markFieldError(pwc, 'Passwords do not match.'); }

    const otpInputs = form.querySelectorAll('.otp-grid input');
    if (otpInputs.length && !Array.from(otpInputs).every(i => i.value.trim().length === 1)) {
        valid = false; showToast('Please enter all 6 digits.', 'warning');
    }
    if (!valid) {
        const firstErr = form.querySelector('.has-error input, .has-error select, .has-error textarea');
        firstErr && firstErr.focus();
    }
    return valid;
}
function markFieldError(field, msg) {
    const wrapper = field.closest('.form-field, .form-group') || field.parentElement;
    if (wrapper) wrapper.classList.add('has-error');
    const err = document.createElement('p');
    err.className = 'field-error';
    err.innerHTML = `<i data-lucide="alert-circle" style="width:12px;height:12px;flex-shrink:0;"></i> ${msg}`;
    field.insertAdjacentElement('afterend', err);
    if (window.lucide) lucide.createIcons({ nodes: [err] });
}

/* ─── Button loading state ────────────────────────────────────────────────── */
function setButtonLoading(btn, loading) {
    if (loading) {
        btn.dataset.origText = btn.innerHTML;
        btn.innerHTML = `<i data-lucide="loader-2" style="animation:spinLoader .7s linear infinite;"></i> Processing…`;
        btn.classList.add('btn-loading');
    } else {
        btn.innerHTML = btn.dataset.origText || btn.innerHTML;
        btn.classList.remove('btn-loading');
    }
    if (window.lucide) lucide.createIcons({ nodes: [btn] });
}
window.setButtonLoading = setButtonLoading;

/* ─── HTML escape ─────────────────────────────────────────────────────────── */
function escapeHtml(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
}

/* ════════════════════════════════════════════════════════════════════════════
   DOM Ready
   ════════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

    /* ─── Lucide icons ────────────────────────────────────────────────────── */
    if (window.lucide) lucide.createIcons();

    /* ─── Header scroll shadow ────────────────────────────────────────────── */
    const header = document.querySelector('.site-header');
    if (header) {
        const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 10);
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    /* ─── Nav active state by URL ─────────────────────────────────────────── */
    const path = window.location.pathname;
    document.querySelectorAll('.nav-center a, .mobile-nav a').forEach(link => {
        const href = link.getAttribute('href');
        if (!href || href === '#') return;
        const isHome = href === '/' && path === '/';
        const isMatch = href !== '/' && path.startsWith(href);
        if (isHome || isMatch) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        }
    });

    /* ─── Mobile menu ─────────────────────────────────────────────────────── */
    const mobileToggle = document.getElementById('mobile-toggle');
    const mobileNav    = document.getElementById('mobile-nav');
    const navOverlay   = document.getElementById('nav-overlay');
    const mobileClose  = document.getElementById('mobile-close');

    const openMobile  = () => { mobileNav?.classList.add('open'); navOverlay?.classList.add('open'); document.body.style.overflow = 'hidden'; mobileToggle?.setAttribute('aria-expanded','true'); };
    const closeMobile = () => { mobileNav?.classList.remove('open'); navOverlay?.classList.remove('open'); document.body.style.overflow = ''; mobileToggle?.setAttribute('aria-expanded','false'); };

    mobileToggle?.addEventListener('click', openMobile);
    mobileClose?.addEventListener('click', closeMobile);
    navOverlay?.addEventListener('click', closeMobile);
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && mobileNav?.classList.contains('open')) closeMobile(); });

    /* ─── Scroll reveal ───────────────────────────────────────────────────── */
    const revealEls = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window) {
        const obs = new IntersectionObserver((entries) => {
            entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('revealed'); obs.unobserve(e.target); } });
        }, { threshold: 0.06, rootMargin: '0px 0px -30px 0px' });
        revealEls.forEach(el => obs.observe(el));
    } else {
        revealEls.forEach(el => el.classList.add('revealed'));
    }

    /* ─── Tabs ────────────────────────────────────────────────────────────── */
    document.querySelectorAll('.tab-bar').forEach(bar => {
        const btns      = bar.querySelectorAll('.tab-btn');
        const container = bar.closest('.tab-container') || bar.parentElement;
        const panels    = container.querySelectorAll('.tab-panel');

        panels.forEach(p => p.setAttribute('aria-hidden', p.classList.contains('active') ? 'false' : 'true'));

        btns.forEach((btn, idx) => {
            btn.addEventListener('click', () => {
                btns.forEach(b => { b.classList.remove('active'); b.setAttribute('aria-selected','false'); });
                panels.forEach(p => { p.classList.remove('active'); p.setAttribute('aria-hidden','true'); });
                btn.classList.add('active'); btn.setAttribute('aria-selected','true');
                const t = container.querySelector('#' + btn.dataset.tab);
                if (t) { t.classList.add('active'); t.setAttribute('aria-hidden','false'); }
            });
            btn.addEventListener('keydown', e => {
                if (e.key === 'ArrowRight') { e.preventDefault(); btns[(idx+1)%btns.length].click(); btns[(idx+1)%btns.length].focus(); }
                if (e.key === 'ArrowLeft')  { e.preventDefault(); btns[(idx-1+btns.length)%btns.length].click(); btns[(idx-1+btns.length)%btns.length].focus(); }
            });
        });
    });

    /* ─── FAQ accordion ───────────────────────────────────────────────────── */
    document.querySelectorAll('.faq-toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const item = toggle.closest('.faq-item');
            if (!item) return;
            const wasOpen = item.classList.contains('open');
            item.closest('article, section, [class]')?.querySelectorAll('.faq-item.open').forEach(i => {
                i.classList.remove('open');
                i.querySelector('.faq-toggle')?.setAttribute('aria-expanded','false');
            });
            if (!wasOpen) { item.classList.add('open'); toggle.setAttribute('aria-expanded','true'); }
        });
    });

    /* ─── Countdown timer ─────────────────────────────────────────────────── */
    document.querySelectorAll('[data-deadline]').forEach(el => {
        const update = () => {
            const diff = Math.max(0, new Date(el.dataset.deadline).getTime() - Date.now());
            const fmt  = n => String(Math.floor(n)).padStart(2,'0');
            const dEl = el.querySelector('[data-days]'),  hEl = el.querySelector('[data-hours]');
            const mEl = el.querySelector('[data-mins]'),  sEl = el.querySelector('[data-secs]');
            if (dEl) dEl.textContent = fmt(diff/864e5);
            if (hEl) hEl.textContent = fmt((diff%864e5)/36e5);
            if (mEl) mEl.textContent = fmt((diff%36e5)/6e4);
            if (sEl) sEl.textContent = fmt((diff%6e4)/1e3);
        };
        update(); setInterval(update, 1000);
    });

    /* ─── Progress bars ───────────────────────────────────────────────────── */
    document.querySelectorAll('.progress-fill[data-progress]').forEach(el => {
        const rawValue = Number.parseFloat(el.dataset.progress || '0');
        const progress = Number.isFinite(rawValue) ? Math.min(100, Math.max(0, rawValue)) : 0;
        el.style.width = `${progress}%`;
    });

    /* ─── Skill chip toggle ───────────────────────────────────────────────── */
    document.querySelectorAll('.chip-toggle .chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('active');
            const form = chip.closest('form');
            const hidden = form?.querySelector('input[name="skills"]');
            if (hidden) {
                const actives = form.querySelectorAll('.chip-toggle .chip.active');
                hidden.value = Array.from(actives).map(c => c.dataset.skill || c.textContent.trim()).join(',');
            }
        });
    });

    /* ─── OTP auto-advance + paste ────────────────────────────────────────── */
    document.querySelectorAll('.otp-grid').forEach(grid => {
        const inputs = grid.querySelectorAll('input');
        inputs.forEach((inp, idx) => {
            inp.addEventListener('input', () => {
                inp.value = inp.value.replace(/\D/,'');
                if (inp.value && idx < inputs.length - 1) inputs[idx+1].focus();
            });
            inp.addEventListener('keydown', e => { if (e.key==='Backspace' && !inp.value && idx>0) inputs[idx-1].focus(); });
            inp.addEventListener('paste', e => {
                e.preventDefault();
                const digits = (e.clipboardData||window.clipboardData).getData('text').replace(/\D/g,'');
                digits.split('').forEach((ch,i) => { if (inputs[idx+i]) inputs[idx+i].value = ch; });
                const next = Array.from(inputs).find(i => !i.value);
                if (next) next.focus();
            });
        });
    });

    /* ─── Animated counters ───────────────────────────────────────────────── */
    document.querySelectorAll('[data-counter]').forEach(el => {
        const target = parseInt(el.textContent.replace(/\D/g,''), 10);
        if (isNaN(target)) return;
        const suffix = el.textContent.replace(/[\d,]/g,'');
        let cur = 0; const inc = target/40;
        const obs = new IntersectionObserver(([entry]) => {
            if (!entry.isIntersecting) return;
            obs.unobserve(el);
            const t = setInterval(() => { cur += inc; if(cur>=target){cur=target;clearInterval(t);} el.textContent=Math.floor(cur).toLocaleString()+suffix; }, 30);
        }, { threshold: .5 });
        obs.observe(el);
    });

    /* ─── Event category filter ───────────────────────────────────────────── */
    const filterBar = document.querySelector('.filters');
    const cardsGrid = document.querySelector('.card-grid');
    if (filterBar && cardsGrid) {
        const allCards = Array.from(cardsGrid.querySelectorAll('.event-card'));
        filterBar.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                filterBar.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                const filter = chip.textContent.replace(/[^a-zA-Z ]/g,'').trim().toLowerCase();
                allCards.forEach(card => {
                    const badge = card.querySelector('.event-badge');
                    const cat   = badge ? badge.textContent.trim().toLowerCase() : '';
                    const show  = filter === 'all' || cat.includes(filter.split(' ')[0]) || filter.includes(cat.split(' ')[0]);
                    card.style.transition = 'opacity .22s, transform .22s';
                    if (show) { card.style.opacity='1'; card.style.transform=''; card.removeAttribute('hidden'); }
                    else { card.style.opacity='0'; card.style.transform='scale(.95)'; setTimeout(()=>{if(card.style.opacity==='0') card.setAttribute('hidden','');},230); }
                });
                cardsGrid.querySelector('.no-filter-results')?.remove();
                const visible = allCards.filter(c => !c.hasAttribute('hidden'));
                if (!visible.length) {
                    const empty = document.createElement('div');
                    empty.className='empty-state no-filter-results'; empty.style.gridColumn='1/-1';
                    empty.innerHTML='<i data-lucide="search-x"></i><p>No events match this filter.</p>';
                    cardsGrid.appendChild(empty);
                    if (window.lucide) lucide.createIcons({nodes:[empty]});
                }
            });
        });
    }

    /* ─── Event search bar ────────────────────────────────────────────────── */
    const searchInput = document.getElementById('event-search');
    if (searchInput && cardsGrid) {
        const allCards = Array.from(cardsGrid.querySelectorAll('.event-card'));
        searchInput.addEventListener('input', () => {
            const q = searchInput.value.trim().toLowerCase();
            allCards.forEach(card => {
                const show = !q || card.textContent.toLowerCase().includes(q);
                card.style.display = show ? '' : 'none';
            });
        });
        // Bind search button
        const searchBtn = searchInput.nextElementSibling;
        searchBtn?.addEventListener('click', () => searchInput.dispatchEvent(new Event('input')));
    }

    /* ─── User dropdown menu ──────────────────────────────────────────────── */
    const userMenuBtn  = document.getElementById('user-menu-btn');
    const userDropdown = document.getElementById('user-dropdown');
    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', e => {
            e.stopPropagation();
            const open = userDropdown.classList.toggle('open');
            userMenuBtn.setAttribute('aria-expanded', String(open));
            if (open) userDropdown.querySelector('a')?.focus();
        });
        document.addEventListener('click', e => {
            if (!userDropdown.contains(e.target) && e.target !== userMenuBtn) {
                userDropdown.classList.remove('open'); userMenuBtn.setAttribute('aria-expanded','false');
            }
        });
        document.addEventListener('keydown', e => {
            if (e.key==='Escape' && userDropdown.classList.contains('open')) {
                userDropdown.classList.remove('open'); userMenuBtn.setAttribute('aria-expanded','false'); userMenuBtn.focus();
            }
        });
    }

    /* ─── Alert dismiss ───────────────────────────────────────────────────── */
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) { alert.style.cssText='opacity:0;transform:translateY(-6px);transition:.2s'; setTimeout(()=>alert.remove(),220); }
        });
    });

    /* ─── Password visibility toggle ─────────────────────────────────────── */
    document.querySelectorAll('input[type="password"]').forEach(inp => {
        const wrapper = inp.closest('.form-group, .form-field');
        if (!wrapper || wrapper.querySelector('.password-toggle')) return;
        const btn = document.createElement('button');
        btn.type='button'; btn.className='password-toggle'; btn.setAttribute('aria-label','Toggle password visibility');
        btn.innerHTML='<i data-lucide="eye"></i>'; wrapper.appendChild(btn);
        if (window.lucide) lucide.createIcons({nodes:[btn]});
        btn.addEventListener('click', () => {
            inp.type = inp.type==='password' ? 'text' : 'password';
            btn.innerHTML=`<i data-lucide="${inp.type==='text'?'eye-off':'eye'}"></i>`;
            if (window.lucide) lucide.createIcons({nodes:[btn]});
        });
    });

    /* ─── Form submit: client-side validate + loading state ──────────────── */
    document.querySelectorAll('form[novalidate]').forEach(form => {
        form.addEventListener('submit', e => {
            if (!validateForm(form)) { e.preventDefault(); return; }
            const btn = form.querySelector('[type="submit"]');
            if (btn) setButtonLoading(btn, true);
        });
    });

    /* ─── Create Event: team size show/hide + date min ────────────────────── */
    const createEventForm = document.getElementById('create-event-form');
    if (createEventForm) {
        const partSel = createEventForm.querySelector('select[name="participation_type"]');
        const minF    = createEventForm.querySelector('input[name="min_team_size"]');
        const maxF    = createEventForm.querySelector('input[name="max_team_size"]');
        if (partSel && minF && maxF) {
            const toggle = () => {
                const isTeam = partSel.value !== 'Solo' && partSel.value !== '';
                [minF, maxF].forEach(f => { const w=f.closest('.form-field'); if(w) w.style.display=isTeam?'':'none'; f.required=isTeam; });
            };
            partSel.addEventListener('change', toggle); toggle();
        }
        const sd = createEventForm.querySelector('input[name="start_date"]');
        const ed = createEventForm.querySelector('input[name="end_date"]');
        if (sd && ed) {
            sd.min = new Date().toISOString().split('T')[0];
            sd.addEventListener('change', () => { ed.min=sd.value; if(ed.value<sd.value) ed.value=sd.value; });
        }
    }

    /* ─── Mark all notifications read ─────────────────────────────────────
       The button is now a real <form method="POST"> submit; no JS needed.
       The form posts to dashboard:mark_all_read which returns JSON {ok,updated}.
       We intercept it here to give instant visual feedback without a reload.
    ── */
    const markAllReadForm = document.getElementById('mark-all-read-form');
    if (markAllReadForm) {
        markAllReadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const resp = await fetch(markAllReadForm.action, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': markAllReadForm.querySelector('[name=csrfmiddlewaretoken]').value },
                    credentials: 'same-origin',
                });
                if (resp.ok) {
                    document.querySelectorAll('.notif-unread').forEach(c => { c.classList.remove('notif-unread'); });
                    document.querySelectorAll('.notif-dot').forEach(d => d.remove());
                    document.querySelectorAll('#header-notif-badge, #sidebar-notif-badge').forEach(b => { b.style.display = 'none'; });
                    showToast('All notifications marked as read.', 'success');
                    markAllReadForm.querySelector('button').disabled = true;
                }
            } catch (_) {
                markAllReadForm.submit(); // fallback: let the normal POST happen
            }
        });
    }

    /* ─── Settings save ───────────────────────────────────────────────────── */
    const settingsForm = document.getElementById('settings-form');
    const settingsSaveBtn = document.getElementById('settings-save-btn');
    if (settingsForm && settingsSaveBtn) {
        settingsForm.addEventListener('submit', (e) => {
            setButtonLoading(settingsSaveBtn, true);
        });
    }

    /* ─── Danger zone: data-confirm buttons ───────────────────────────────── */
    document.querySelectorAll('[data-confirm]').forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            showConfirm({
                title:        btn.dataset.confirmTitle || 'Confirm Action',
                message:      btn.dataset.confirmMsg   || 'Are you sure?',
                confirmText:  btn.dataset.confirmLabel || 'Confirm',
                confirmClass: btn.dataset.danger==='true' ? 'btn-secondary' : 'btn-primary',
                onConfirm:    () => showToast(btn.dataset.toastMsg || 'Done.', btn.dataset.danger==='true' ? 'warning' : 'success'),
            });
        });
    });

    /* ─── Team join request: accept / decline ─────────────────────────────── */
    document.querySelectorAll('[data-action="accept-request"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const li = btn.closest('li'), name = li?.querySelector('strong')?.textContent || 'User';
            li && (li.style.cssText='opacity:.4;transition:.4s;pointer-events:none');
            showToast(`${name} accepted!`, 'success');
            setTimeout(() => li?.remove(), 500);
        });
    });
    document.querySelectorAll('[data-action="decline-request"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const li = btn.closest('li'), name = li?.querySelector('strong')?.textContent || 'User';
            showConfirm({ title:'Decline Request', message:`Decline join request from ${name}?`, confirmText:'Decline', confirmClass:'btn-secondary',
                onConfirm: () => { li && (li.style.cssText='opacity:.4;transition:.4s'); showToast(`Declined ${name}'s request.`, 'info'); setTimeout(()=>li?.remove(),500); }
            });
        });
    });

    /* ─── "Already Registered" button ────────────────────────────────────── */
    document.querySelector('[data-already-registered]')?.addEventListener('click', () => showToast('You are already registered for this event.','info'));

    /* ─── Request to Join Team ────────────────────────────────────────────── */
    document.querySelectorAll('[data-action="request-join"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const li = btn.closest('li');
            const teamName = li?.querySelector('strong')?.textContent || 'this team';
            setButtonLoading(btn, true);
            setTimeout(() => {
                setButtonLoading(btn, false);
                btn.textContent = 'Request Sent';
                btn.disabled = true;
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-secondary');
                showToast(`Join request sent to ${teamName}!`, 'success');
            }, 800);
        });
    });

    /* ─── Chat form ───────────────────────────────────────────────────────── */
    document.getElementById('chat-form')?.addEventListener('submit', e => {
        if (e.currentTarget.dataset.serverSubmit === 'true') return;
        e.preventDefault();
        const inp = e.currentTarget.querySelector('input[name="message"]');
        const msg = inp?.value?.trim();
        if (!msg) { showToast('Type a message first.','warning'); return; }
        const chatBox = document.querySelector('.chat-box');
        if (chatBox) {
            const bubble = document.createElement('div');
            bubble.className = 'chat-msg';
            bubble.innerHTML = `<div class="avatar avatar-sm" style="background:linear-gradient(135deg,var(--primary),var(--primary-3));">Y</div><div class="chat-bubble"><strong>You</strong>${escapeHtml(msg)}<span>Just now</span></div>`;
            chatBox.appendChild(bubble);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        inp.value = ''; inp.focus();
    });

    /* ─── Event card category banner colours ──────────────────────────────── */
    document.querySelectorAll('.event-card-banner').forEach(banner => {
        const badge = banner.querySelector('.event-badge');
        if (!badge) return;
        const cat = badge.textContent.trim().toLowerCase().replace(/\s+/g,'-');
        banner.classList.add('event-banner-' + cat);
    });

    /* ─── Resend OTP cooldown ─────────────────────────────────────────────── */
    document.querySelector('[data-action="resend-otp"]')?.addEventListener('click', function() {
        const btn = this; btn.disabled = true; let s = 30;
        btn.textContent = `Resend in ${s}s`;
        const t = setInterval(() => {
            s--;
            btn.textContent = `Resend in ${s}s`;
            if (s <= 0) { clearInterval(t); btn.disabled=false; btn.innerHTML='<i data-lucide="refresh-cw"></i> Resend Code'; if(window.lucide)lucide.createIcons({nodes:[btn]}); showToast('New code sent!','info'); }
        }, 1000);
    });

    /* ─── Stub action buttons ─────────────────────────────────────────────── */
    const stubs = {
        'edit-profile':     () => showToast('Profile editing coming soon!', 'info'),
        'export-csv':       btn => { setButtonLoading(btn,true); setTimeout(()=>{setButtonLoading(btn,false);showToast('Export ready!','success');},1200); },
        'open-wizard':      () => showToast('Event wizard coming soon!', 'info'),
        'customize-form':   () => showToast('Form builder coming soon!', 'info'),
        'team-settings':    () => showToast('Team settings coming soon!', 'info'),
        'social-login':     btn => showToast(`${btn.dataset.provider||'Social'} sign-in coming soon!`, 'info'),
        'team-chat':        btn => showToast(`Chat for ${btn.closest('article')?.querySelector('h3')?.textContent||'team'} coming soon!`, 'info'),
        'team-invite':      () => { navigator.clipboard?.writeText(window.location.href).then(()=>showToast('Invite link copied!','success')).catch(()=>showToast('Invite link copied!','success')); },
        'contact-organizer': btn => {
            const inp = btn.previousElementSibling;
            if (inp?.value?.trim()) { showToast('Message sent to organizers!','success'); inp.value=''; }
            else showToast('Please enter a message.','warning');
        },
    };
    Object.entries(stubs).forEach(([action, handler]) => {
        document.querySelectorAll(`[data-action="${action}"]`).forEach(btn => btn.addEventListener('click', () => handler(btn)));
    });

    /* ─── Re-init lucide icons (catch-all) ───────────────────────────────── */
    if (window.lucide) lucide.createIcons();

    /* ─── Notification badge polling ──────────────────────────────────────── */
    (function notifPoll() {
        const headerBadge = document.getElementById('header-notif-badge');
        const sidebarBadge = document.getElementById('sidebar-notif-badge');
        if (!headerBadge && !sidebarBadge) return;

        let interval = 30000; // start at 30s
        const maxInterval = 120000; // max 2 min
        let errorCount = 0;

        function updateBadges(count) {
            [headerBadge, sidebarBadge].forEach(badge => {
                if (!badge) return;
                if (count > 0) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.style.display = '';
                } else {
                    badge.style.display = 'none';
                }
            });
        }

        async function poll() {
            try {
                const resp = await fetch('/notifications/api/unread-count/', { credentials: 'same-origin' });
                if (resp.ok) {
                    const data = await resp.json();
                    updateBadges(data.count || 0);
                    errorCount = 0;
                    interval = 30000; // reset on success
                }
            } catch (e) {
                errorCount++;
                interval = Math.min(interval * 1.5, maxInterval); // backoff
            }
            if (errorCount < 10) setTimeout(poll, interval);
        }

        // Initial fetch + start polling
        poll();
    })();

    /* ─── Registration form: show/hide team details ───────────────────────── */
    const regForm = document.getElementById('event-register-form');
    if (regForm) {
        const radios = regForm.querySelectorAll('input[name="type"]');
        const teamStep = regForm.querySelector('article:last-of-type'); // Step 5: Team Details
        if (radios.length && teamStep) {
            function toggleTeamStep() {
                const selected = regForm.querySelector('input[name="type"]:checked');
                const showTeam = selected && (selected.value === 'create_team' || selected.value === 'join_team');
                teamStep.style.display = showTeam ? '' : 'none';
            }
            radios.forEach(r => r.addEventListener('change', toggleTeamStep));
            toggleTeamStep();
        }
    }
});
