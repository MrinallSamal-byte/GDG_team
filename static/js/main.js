/**
 * CampusArena — Main JavaScript
 * Theme toggle, micro-interactions, WebSocket connections, AJAX utilities
 */

document.addEventListener('DOMContentLoaded', function () {
    initThemeToggle();
    initMessageDismiss();
    initAccordions();
    initTabs();
    initMobileNav();
    initCountdowns();
    initSmoothScrolling();
});


// ─── Theme Toggle ───
function initThemeToggle() {
    const toggles = document.querySelectorAll('.theme-toggle');

    toggles.forEach(toggle => {
        toggle.addEventListener('click', async function () {
            const csrfToken = getCSRFToken();

            try {
                const response = await fetch('/auth/toggle-theme/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json',
                    },
                });

                const data = await response.json();
                document.documentElement.setAttribute('data-theme', data.theme);

                // Smooth transition
                document.body.style.transition = 'background-color 0.4s, color 0.4s';

            } catch (err) {
                // Fallback: toggle locally
                const current = document.documentElement.getAttribute('data-theme') || 'light';
                const next = current === 'light' ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', next);
                document.cookie = `theme=${next};path=/;max-age=${365 * 24 * 60 * 60};SameSite=Lax`;
            }
        });
    });
}


// ─── Message Dismiss ───
function initMessageDismiss() {
    document.querySelectorAll('.message-close').forEach(btn => {
        btn.addEventListener('click', function () {
            const alert = this.closest('.message-alert');
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 200);
        });
    });

    // Auto-dismiss after 5s
    document.querySelectorAll('.message-alert').forEach(alert => {
        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                setTimeout(() => alert.remove(), 200);
            }
        }, 5000);
    });
}


// ─── Accordions ───
function initAccordions() {
    document.querySelectorAll('.accordion-trigger').forEach(trigger => {
        trigger.addEventListener('click', function () {
            const item = this.closest('.accordion-item');
            const content = item.querySelector('.accordion-content');
            const isOpen = item.classList.contains('open');

            // Close all
            this.closest('.accordion').querySelectorAll('.accordion-item').forEach(i => {
                i.classList.remove('open');
                i.querySelector('.accordion-content').style.maxHeight = '0';
            });

            // Toggle current
            if (!isOpen) {
                item.classList.add('open');
                content.style.maxHeight = content.scrollHeight + 'px';
            }
        });
    });
}


// ─── Tabs ───
function initTabs() {
    document.querySelectorAll('[data-tab]').forEach(tab => {
        tab.addEventListener('click', function () {
            const group = this.closest('.tabs-container');
            if (!group) return;

            // Update active tab
            group.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Show target content
            const targetId = this.dataset.tab;
            group.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            const target = document.getElementById(targetId);
            if (target) target.classList.add('active');
        });
    });
}


// ─── Mobile Nav ───
function initMobileNav() {
    const toggle = document.querySelector('.mobile-nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (toggle && navLinks) {
        toggle.addEventListener('click', function () {
            navLinks.classList.toggle('mobile-open');
            this.classList.toggle('active');
        });
    }
}


// ─── Countdown Timers ───
function initCountdowns() {
    document.querySelectorAll('[data-countdown]').forEach(el => {
        const target = new Date(el.dataset.countdown).getTime();

        function update() {
            const now = Date.now();
            const diff = target - now;

            if (diff <= 0) {
                el.innerHTML = '<span class="tag tag-danger">Deadline passed</span>';
                return;
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const secs = Math.floor((diff % (1000 * 60)) / 1000);

            el.innerHTML = `
        <div class="countdown-unit"><div class="countdown-value">${days}</div><div class="countdown-label">Days</div></div>
        <div class="countdown-unit"><div class="countdown-value">${hours}</div><div class="countdown-label">Hours</div></div>
        <div class="countdown-unit"><div class="countdown-value">${mins}</div><div class="countdown-label">Min</div></div>
        <div class="countdown-unit"><div class="countdown-value">${secs}</div><div class="countdown-label">Sec</div></div>
      `;

            requestAnimationFrame(() => setTimeout(update, 1000));
        }

        update();
    });
}


// ─── Smooth Scrolling ───
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}


// ─── WebSocket Connections ───
function connectWebSocket(path, onMessage) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}${path}`;

    const ws = new WebSocket(url);

    ws.onmessage = function (e) {
        const data = JSON.parse(e.data);
        onMessage(data);
    };

    ws.onclose = function () {
        // Reconnect after 3s
        setTimeout(() => connectWebSocket(path, onMessage), 3000);
    };

    return ws;
}


// ─── Chat WebSocket ───
function initChat(teamId) {
    const messagesContainer = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');

    if (!messagesContainer || !chatInput) return;

    const ws = connectWebSocket(`/ws/team/${teamId}/chat/`, function (data) {
        appendMessage(messagesContainer, data);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });

    function send() {
        const message = chatInput.value.trim();
        if (message && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message: message }));
            chatInput.value = '';
        }
    }

    if (sendBtn) sendBtn.addEventListener('click', send);
    chatInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') send();
    });

    // Scroll to bottom on load
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendMessage(container, data) {
    const div = document.createElement('div');
    const isOwn = data.sender_id === window.currentUserId;
    const isSystem = data.message_type === 'system';

    div.className = `chat-message ${isOwn ? 'own' : ''} ${isSystem ? 'system' : ''}`;

    if (isSystem) {
        div.innerHTML = `<div class="chat-bubble">${data.content}</div>`;
    } else {
        div.innerHTML = `
      <div class="avatar avatar-sm">${data.sender_initials || data.sender_name?.substring(0, 2) || '?'}</div>
      <div class="chat-bubble">
        <div class="sender-name text-xs font-medium">${data.sender_name}</div>
        ${data.content}
        <div class="meta">${new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      </div>
    `;
    }

    container.appendChild(div);
}


// ─── Notification Badge ───
function initNotifications() {
    connectWebSocket('/ws/notifications/', function (data) {
        const badge = document.querySelector('.notification-badge .count');
        if (badge) {
            const current = parseInt(badge.textContent || '0');
            badge.textContent = current + 1;
            badge.style.display = 'flex';
        }

        // Show toast
        showToast(data.title || 'New notification', 'info');
    });
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `message-alert ${type}`;
    toast.style.cssText = `
    position: fixed; top: 80px; right: 20px; z-index: 1000;
    min-width: 280px; animation: slideDown 0.3s ease;
  `;
    toast.innerHTML = `
    ${message}
    <button class="message-close" onclick="this.parentElement.remove()">&times;</button>
  `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}


// ─── CSRF Token ───
function getCSRFToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    if (cookie) return cookie.split('=')[1];
    const meta = document.querySelector('[name=csrfmiddlewaretoken]');
    if (meta) return meta.value;
    return '';
}


// ─── Mark Notification Read ───
async function markNotificationRead(id, element) {
    try {
        await fetch(`/notifications/${id}/read/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        if (element) element.classList.add('read');
    } catch (err) {
        console.error('Failed to mark notification read:', err);
    }
}
