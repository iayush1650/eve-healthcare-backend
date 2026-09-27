/* ═══════════════════════════════════════════════════════════════════════════
   EVE Healthcare — Frontend Application Logic
   Connects to FastAPI backend at localhost:8000
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = 'http://127.0.0.1:8000/api/v1';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
    token: localStorage.getItem('eve_token') || null,
    user: JSON.parse(localStorage.getItem('eve_user') || 'null'),
    currentPage: 'home',
    centres: [],
    bookings: [],
};

// ── DOM References ─────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── API Helper ─────────────────────────────────────────────────────────────
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const data = await res.json().catch(() => null);

    if (!res.ok) {
        const msg = data?.detail || data?.errors?.[0]?.message || `Error ${res.status}`;
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
}

// ── Toast Notifications ────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('leaving');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ── Navigation ─────────────────────────────────────────────────────────────
function navigateTo(page) {
    state.currentPage = page;

    // Update pages
    $$('.page').forEach(p => p.classList.remove('active'));
    const target = $(`#page-${page}`);
    if (target) target.classList.add('active');

    // Update nav links
    $$('.nav-link').forEach(l => {
        l.classList.toggle('active', l.dataset.page === page);
    });

    // Close mobile menu
    $('#nav-links').classList.remove('open');

    // Load data
    if (page === 'centres') loadCentres();
    if (page === 'bookings') loadBookings();

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Auth ───────────────────────────────────────────────────────────────────
function updateAuthUI() {
    const actions = $('#nav-actions');
    if (state.user) {
        const initials = state.user.full_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        actions.innerHTML = `
            <div class="user-pill">
                <div class="user-avatar">${initials}</div>
                <span class="user-name">${state.user.full_name}</span>
            </div>
            <button class="btn btn-outline btn-sm" id="logout-btn">Logout</button>
        `;
        $('#logout-btn').addEventListener('click', logout);
    } else {
        actions.innerHTML = `
            <button class="btn btn-glass btn-sm" id="open-login-btn">Login</button>
            <button class="btn btn-primary btn-sm" id="open-signup-btn">Sign Up</button>
        `;
        $('#open-login-btn').addEventListener('click', () => openAuthModal('login'));
        $('#open-signup-btn').addEventListener('click', () => openAuthModal('signup'));
    }
}

function openAuthModal(tab = 'login') {
    $('#auth-modal').classList.add('active');
    switchAuthTab(tab);
}

function closeAuthModal() {
    $('#auth-modal').classList.remove('active');
    $('#login-error').textContent = '';
    $('#signup-error').textContent = '';
}

function switchAuthTab(tab) {
    $$('.auth-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    $('#login-form').style.display = tab === 'login' ? 'block' : 'none';
    $('#signup-form').style.display = tab === 'signup' ? 'block' : 'none';
}

async function handleLogin(e) {
    e.preventDefault();
    const btn = $('#login-submit-btn');
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');

    text.style.display = 'none';
    loader.style.display = 'block';
    btn.disabled = true;

    try {
        const data = await api('/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: $('#login-email').value,
                password: $('#login-password').value,
            }),
        });

        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('eve_token', state.token);
        localStorage.setItem('eve_user', JSON.stringify(state.user));

        updateAuthUI();
        closeAuthModal();
        showToast(`Welcome back, ${state.user.full_name}!`, 'success');
        $('#login-form').reset();
    } catch (err) {
        $('#login-error').textContent = err.message;
    } finally {
        text.style.display = 'inline';
        loader.style.display = 'none';
        btn.disabled = false;
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const btn = $('#signup-submit-btn');
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');

    text.style.display = 'none';
    loader.style.display = 'block';
    btn.disabled = true;

    try {
        const body = {
            full_name: $('#signup-name').value,
            email: $('#signup-email').value,
            password: $('#signup-password').value,
        };
        const phone = $('#signup-phone').value.trim();
        if (phone) body.phone = phone;

        const data = await api('/auth/signup', {
            method: 'POST',
            body: JSON.stringify(body),
        });

        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('eve_token', state.token);
        localStorage.setItem('eve_user', JSON.stringify(state.user));

        updateAuthUI();
        closeAuthModal();
        showToast(`Account created! Welcome, ${state.user.full_name}!`, 'success');
        $('#signup-form').reset();
    } catch (err) {
        $('#signup-error').textContent = err.message;
    } finally {
        text.style.display = 'inline';
        loader.style.display = 'none';
        btn.disabled = false;
    }
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('eve_token');
    localStorage.removeItem('eve_user');
    updateAuthUI();
    navigateTo('home');
    showToast('Logged out successfully', 'info');
}

// ── Centres ────────────────────────────────────────────────────────────────
async function loadCentres(location = '') {
    const grid = $('#centres-grid');
    const loader = $('#centres-loader');
    grid.innerHTML = '';
    loader.style.display = 'flex';

    try {
        let url = '/centres/?page_size=50';
        if (location) url += `&location=${encodeURIComponent(location)}`;

        const data = await api(url);
        state.centres = data.centres;
        loader.style.display = 'none';

        if (data.centres.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column:1/-1;">
                    <div class="empty-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="1.5"/></svg>
                    </div>
                    <h3>No centres found</h3>
                    <p>Try a different location or clear the search</p>
                </div>
            `;
            return;
        }

        data.centres.forEach((centre, i) => {
            const el = document.createElement('div');
            el.className = 'centre-card';
            el.style.animation = `fadeInUp 0.4s ease ${i * 0.08}s both`;

            const initials = centre.name.split(' ').map(w => w[0]).join('').slice(0, 2);
            const testCount = centre.tests?.length || 0;
            const prices = (centre.tests || []).map(t => parseFloat(t.price));
            const minPrice = prices.length ? Math.min(...prices) : 0;
            const maxPrice = prices.length ? Math.max(...prices) : 0;

            const testTags = (centre.tests || []).slice(0, 4).map(t =>
                `<span class="test-tag">${t.test_name.split('(')[0].trim()}</span>`
            ).join('');
            const moreCount = testCount > 4 ? `<span class="test-tag">+${testCount - 4} more</span>` : '';

            el.innerHTML = `
                <div class="centre-header">
                    <div class="centre-avatar">${initials}</div>
                    <div class="centre-info">
                        <div class="centre-name">${centre.name}</div>
                        <div class="centre-location">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="2"/></svg>
                            ${centre.location}
                        </div>
                    </div>
                </div>
                <div class="centre-meta">
                    <div class="centre-meta-item">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        ${testCount} tests available
                    </div>
                    ${centre.phone ? `
                    <div class="centre-meta-item">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" stroke="currentColor" stroke-width="2"/></svg>
                        ${centre.phone}
                    </div>` : ''}
                </div>
                <div class="centre-tests-preview">${testTags}${moreCount}</div>
                <div class="centre-footer">
                    <div class="centre-price-range">
                        From <strong>₹${minPrice.toLocaleString()}</strong> — <strong>₹${maxPrice.toLocaleString()}</strong>
                    </div>
                    <button class="btn btn-outline btn-sm">View Details →</button>
                </div>
            `;

            el.addEventListener('click', () => showCentreDetail(centre));
            grid.appendChild(el);
        });
    } catch (err) {
        loader.style.display = 'none';
        showToast('Failed to load centres: ' + err.message, 'error');
    }
}

function showCentreDetail(centre) {
    navigateTo('centre-detail');

    const content = $('#centre-detail-content');
    const testsHtml = (centre.tests || []).map(t => `
        <div class="test-card">
            <div>
                <div class="test-name">${t.test_name}</div>
                <span class="test-category">${t.category || 'General'}</span>
            </div>
            <div>
                <div class="test-price">₹${parseFloat(t.price).toLocaleString()}</div>
                <button class="btn btn-primary btn-sm book-test-btn" 
                    data-centre-test-id="${t.centre_test_id}"
                    data-test-name="${t.test_name}"
                    data-centre-name="${centre.name}"
                    data-price="${t.price}">
                    Book Now
                </button>
            </div>
        </div>
    `).join('');

    content.innerHTML = `
        <div class="detail-header">
            <button class="detail-back" id="detail-back-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M19 12H5m7-7l-7 7 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                Back to Centres
            </button>
            <div class="detail-hero">
                <div class="detail-top">
                    <div>
                        <h1 class="detail-name">${centre.name}</h1>
                        <span class="detail-status status-active">● Active</span>
                    </div>
                </div>
                <div class="detail-info">
                    <div class="detail-info-item">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="2"/></svg>
                        ${centre.location}
                    </div>
                    ${centre.address ? `
                    <div class="detail-info-item">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="currentColor" stroke-width="2"/><polyline points="9,22 9,12 15,12 15,22" stroke="currentColor" stroke-width="2"/></svg>
                        ${centre.address}
                    </div>` : ''}
                    ${centre.phone ? `
                    <div class="detail-info-item">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" stroke="currentColor" stroke-width="2"/></svg>
                        ${centre.phone}
                    </div>` : ''}
                </div>
            </div>
        </div>
        <div class="detail-section">
            <h2 class="detail-section-title">Available Tests (${centre.tests?.length || 0})</h2>
            <div class="tests-list">${testsHtml || '<p style="color:var(--text-muted);">No tests available at this centre.</p>'}</div>
        </div>
    `;

    // Back button
    $('#detail-back-btn').addEventListener('click', () => navigateTo('centres'));

    // Book buttons
    content.querySelectorAll('.book-test-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!state.user) {
                showToast('Please login to book a test', 'error');
                openAuthModal('login');
                return;
            }
            openBookingModal({
                centreTestId: btn.dataset.centreTestId,
                testName: btn.dataset.testName,
                centreName: btn.dataset.centreName,
                price: btn.dataset.price,
            });
        });
    });
}

// ── Booking Modal ──────────────────────────────────────────────────────────
function openBookingModal(info) {
    const modal = $('#booking-modal');
    const content = $('#booking-modal-content');

    // Default datetime: tomorrow 10 AM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    const dtVal = tomorrow.toISOString().slice(0, 16);

    content.innerHTML = `
        <h2 style="font-family:var(--font-display);font-weight:700;margin-bottom:4px;">Book Test</h2>
        <p class="form-subtitle">Confirm your appointment details</p>

        <div class="confirm-details" style="margin-bottom:20px;">
            <div class="confirm-row">
                <span class="confirm-row-label">Test</span>
                <span class="confirm-row-value">${info.testName}</span>
            </div>
            <div class="confirm-row">
                <span class="confirm-row-label">Centre</span>
                <span class="confirm-row-value">${info.centreName}</span>
            </div>
            <div class="confirm-row">
                <span class="confirm-row-label">Price</span>
                <span class="confirm-row-value" style="color:var(--accent-green);">₹${parseFloat(info.price).toLocaleString()}</span>
            </div>
        </div>

        <form id="booking-form">
            <div class="form-group">
                <label for="booking-datetime">Appointment Date & Time</label>
                <input type="datetime-local" id="booking-datetime" value="${dtVal}" required>
            </div>
            <div class="form-error" id="booking-error"></div>
            <div style="display:flex;gap:10px;">
                <button type="button" class="btn btn-glass" style="flex:1;" id="booking-cancel-btn">Cancel</button>
                <button type="submit" class="btn btn-primary" style="flex:2;" id="booking-confirm-btn">
                    <span class="btn-text">Confirm Booking</span>
                    <div class="btn-loader" style="display:none;"></div>
                </button>
            </div>
        </form>
    `;

    modal.classList.add('active');

    $('#booking-cancel-btn').addEventListener('click', closeBookingModal);
    $('#booking-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = $('#booking-confirm-btn');
        const text = btn.querySelector('.btn-text');
        const loader = btn.querySelector('.btn-loader');
        text.style.display = 'none';
        loader.style.display = 'block';
        btn.disabled = true;

        try {
            const dt = new Date($('#booking-datetime').value).toISOString();
            const booking = await api('/bookings/', {
                method: 'POST',
                body: JSON.stringify({
                    centre_test_id: info.centreTestId,
                    appointment_datetime: dt,
                }),
            });

            // Show success & ask for payment
            showBookingSuccess(booking, info);
        } catch (err) {
            $('#booking-error').textContent = err.message;
            text.style.display = 'inline';
            loader.style.display = 'none';
            btn.disabled = false;
        }
    });
}

function showBookingSuccess(booking, info) {
    const content = $('#booking-modal-content');
    const apptDate = new Date(booking.appointment_datetime);
    const formattedDate = apptDate.toLocaleDateString('en-IN', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    const formattedTime = apptDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    content.innerHTML = `
        <div class="confirm-content">
            <div class="confirm-icon confirm-icon-success">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <h2 class="confirm-title">Booking Created!</h2>
            <p style="color:var(--text-secondary);margin-bottom:16px;">Your appointment has been scheduled</p>

            <div class="confirm-details">
                <div class="confirm-row">
                    <span class="confirm-row-label">Test</span>
                    <span class="confirm-row-value">${booking.test_name}</span>
                </div>
                <div class="confirm-row">
                    <span class="confirm-row-label">Centre</span>
                    <span class="confirm-row-value">${booking.centre_name}</span>
                </div>
                <div class="confirm-row">
                    <span class="confirm-row-label">Date</span>
                    <span class="confirm-row-value">${formattedDate}</span>
                </div>
                <div class="confirm-row">
                    <span class="confirm-row-label">Time</span>
                    <span class="confirm-row-value">${formattedTime}</span>
                </div>
                <div class="confirm-row">
                    <span class="confirm-row-label">Amount</span>
                    <span class="confirm-row-value" style="color:var(--accent-green);">₹${parseFloat(booking.amount).toLocaleString()}</span>
                </div>
                <div class="confirm-row">
                    <span class="confirm-row-label">Status</span>
                    <span class="confirm-row-value booking-status status-pending">${booking.status}</span>
                </div>
            </div>

            <div style="display:flex;gap:10px;margin-top:20px;">
                <button class="btn btn-glass" style="flex:1;" id="success-close-btn">Close</button>
                <button class="btn btn-primary" style="flex:2;" id="success-pay-btn" data-booking-id="${booking.id}">
                    <span class="btn-text">Pay Now</span>
                    <div class="btn-loader" style="display:none;"></div>
                </button>
            </div>
        </div>
    `;

    $('#success-close-btn').addEventListener('click', () => {
        closeBookingModal();
        showToast('Booking created! Pay anytime from My Bookings.', 'success');
    });

    $('#success-pay-btn').addEventListener('click', async function () {
        const btn = this;
        const text = btn.querySelector('.btn-text');
        const loader = btn.querySelector('.btn-loader');
        text.style.display = 'none';
        loader.style.display = 'block';
        btn.disabled = true;

        try {
            const payment = await api('/payments/', {
                method: 'POST',
                body: JSON.stringify({ booking_id: booking.id }),
            });

            if (payment.status === 'SUCCESS') {
                showToast('Payment successful! Booking confirmed.', 'success');
            } else {
                showToast('Payment failed (simulated). Try again from My Bookings.', 'error');
            }
            closeBookingModal();
        } catch (err) {
            showToast('Payment error: ' + err.message, 'error');
            text.style.display = 'inline';
            loader.style.display = 'none';
            btn.disabled = false;
        }
    });
}

function closeBookingModal() {
    $('#booking-modal').classList.remove('active');
}

// ── Bookings ───────────────────────────────────────────────────────────────
async function loadBookings() {
    if (!state.user) {
        showToast('Please login to view your bookings', 'error');
        openAuthModal('login');
        navigateTo('home');
        return;
    }

    const list = $('#bookings-list');
    const loader = $('#bookings-loader');
    const empty = $('#bookings-empty');

    list.innerHTML = '';
    loader.style.display = 'flex';
    empty.style.display = 'none';

    try {
        const data = await api('/bookings/?page_size=50');
        state.bookings = data.bookings;
        loader.style.display = 'none';

        if (data.bookings.length === 0) {
            empty.style.display = 'block';
            return;
        }

        data.bookings.forEach((b, i) => {
            const el = document.createElement('div');
            el.className = 'booking-card';
            el.style.animation = `fadeInUp 0.4s ease ${i * 0.06}s both`;

            const apptDate = new Date(b.appointment_datetime);
            const formattedDate = apptDate.toLocaleDateString('en-IN', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
            const formattedTime = apptDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
            const statusClass = `status-${b.status.toLowerCase()}`;

            const canCancel = ['PENDING', 'CONFIRMED'].includes(b.status.toUpperCase());
            const canPay = b.status.toUpperCase() === 'PENDING';

            el.innerHTML = `
                <div class="booking-top">
                    <div>
                        <div class="booking-test-name">${b.test_name}</div>
                        <div class="booking-centre-name">${b.centre_name}</div>
                    </div>
                    <span class="booking-status ${statusClass}">${b.status}</span>
                </div>
                <div class="booking-details">
                    <div class="booking-detail-item">
                        <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/><path d="M16 2v4M8 2v4M3 10h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                        ${formattedDate}
                    </div>
                    <div class="booking-detail-item">
                        <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        ${formattedTime}
                    </div>
                    <div class="booking-detail-item">
                        <svg viewBox="0 0 24 24" fill="none"><line x1="12" y1="1" x2="12" y2="23" stroke="currentColor" stroke-width="2"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        ₹${parseFloat(b.amount).toLocaleString()}
                    </div>
                </div>
                <div class="booking-actions">
                    ${canPay ? `<button class="btn btn-success btn-sm pay-booking-btn" data-id="${b.id}">Pay Now</button>` : ''}
                    ${canCancel ? `<button class="btn btn-danger btn-sm cancel-booking-btn" data-id="${b.id}">Cancel</button>` : ''}
                </div>
            `;

            list.appendChild(el);
        });

        // Wire up pay buttons
        list.querySelectorAll('.pay-booking-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                btn.textContent = 'Processing...';
                try {
                    const payment = await api('/payments/', {
                        method: 'POST',
                        body: JSON.stringify({ booking_id: btn.dataset.id }),
                    });
                    if (payment.status === 'SUCCESS') {
                        showToast('Payment successful! Booking confirmed.', 'success');
                    } else {
                        showToast('Payment failed (simulated 30% chance). Try again!', 'error');
                    }
                    loadBookings();
                } catch (err) {
                    showToast('Payment error: ' + err.message, 'error');
                    btn.disabled = false;
                    btn.textContent = 'Pay Now';
                }
            });
        });

        // Wire up cancel buttons
        list.querySelectorAll('.cancel-booking-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('Are you sure you want to cancel this booking?')) return;
                btn.disabled = true;
                btn.textContent = 'Cancelling...';
                try {
                    await api(`/bookings/${btn.dataset.id}/cancel`, { method: 'POST' });
                    showToast('Booking cancelled.', 'info');
                    loadBookings();
                } catch (err) {
                    showToast('Cancel failed: ' + err.message, 'error');
                    btn.disabled = false;
                    btn.textContent = 'Cancel';
                }
            });
        });
    } catch (err) {
        loader.style.display = 'none';
        showToast('Failed to load bookings: ' + err.message, 'error');
    }
}

// ── Event Listeners ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Auth UI
    updateAuthUI();

    // Nav links
    $$('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });

    // Hamburger
    $('#nav-hamburger').addEventListener('click', () => {
        $('#nav-links').classList.toggle('open');
    });

    // Hero buttons
    $('#hero-explore-btn').addEventListener('click', () => navigateTo('centres'));
    $('#hero-learn-btn').addEventListener('click', () => {
        document.getElementById('how-it-works').scrollIntoView({ behavior: 'smooth' });
    });

    // Search
    $('#search-btn').addEventListener('click', () => {
        loadCentres($('#search-input').value.trim());
    });
    $('#search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') loadCentres($('#search-input').value.trim());
    });

    // Auth modal
    $$('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => switchAuthTab(tab.dataset.tab));
    });
    $('#auth-modal-close').addEventListener('click', closeAuthModal);
    $('#auth-modal').addEventListener('click', (e) => {
        if (e.target === $('#auth-modal')) closeAuthModal();
    });

    // Auth forms
    $('#login-form').addEventListener('submit', handleLogin);
    $('#signup-form').addEventListener('submit', handleSignup);

    // Booking modal
    $('#booking-modal-close').addEventListener('click', closeBookingModal);
    $('#booking-modal').addEventListener('click', (e) => {
        if (e.target === $('#booking-modal')) closeBookingModal();
    });

    // Empty state CTA
    $('#empty-explore-btn').addEventListener('click', () => navigateTo('centres'));

    // Navbar scroll effect
    window.addEventListener('scroll', () => {
        $('#navbar').classList.toggle('scrolled', window.scrollY > 20);
    });
});
