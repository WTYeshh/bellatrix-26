/**
 * AEGIS Main Application Shell — Initializes auth, routing, sidebar, and layout.
 */

const AegisApp = (() => {
    let _initialized = false;

    function init() {
        if (_initialized) return;
        _initialized = true;

        // Check for existing session
        const session = AegisAuth.getSession();
        if (session) {
            showApp();
        } else {
            showLogin();
        }

        // Initialize router hash listener
        AegisRouter.init();

        // Track connection
        AegisAPI.setConnectionCallback(connected => {
            updateConnectionStatus(connected);
        });

        // Try connecting to backend
        AegisAPI.healthCheck();
    }

    function showLogin() {
        document.getElementById('login-page').classList.remove('hidden');
        document.getElementById('app-page').classList.add('hidden');
        setupLoginForm();
    }

    function showApp() {
        document.getElementById('login-page').classList.add('hidden');
        document.getElementById('app-page').classList.remove('hidden');
        setupSidebar();
        setupRoutes();
        initEventStream();
        initAutoRefreshPolling();

        // Navigate to hash or default
        const hash = window.location.hash.slice(1) || 'command-center';
        AegisRouter.navigate(hash);
    }

    function initAutoRefreshPolling() {
        if (window._aegisPollInterval) return;
        window._aegisPollInterval = setInterval(async () => {
            if (document.hidden) return;
            const page = AegisRouter.getCurrentPage();
            try {
                if (page === 'command-center' && typeof CommandCenter !== 'undefined' && CommandCenter.loadData) {
                    await CommandCenter.loadData();
                } else if (page === 'infrastructure' && typeof InfraMonitoring !== 'undefined' && InfraMonitoring.load) {
                    await InfraMonitoring.load();
                } else if (page === 'network' && typeof NetworkMonitoring !== 'undefined' && NetworkMonitoring.load) {
                    await NetworkMonitoring.load();
                } else if (page === 'security' && typeof SecurityMonitoring !== 'undefined' && SecurityMonitoring.load) {
                    await SecurityMonitoring.load();
                } else if (page === 'collectors' && typeof CollectorManagement !== 'undefined' && CollectorManagement.load) {
                    await CollectorManagement.load();
                }
            } catch (err) {
                // Polling error silently suppressed
            }
        }, 3500);
    }

    function initEventStream() {
        if (window._aegisEventSource) return;
        try {
            const host = (typeof AegisAPI !== 'undefined' && AegisAPI.getHost) ? AegisAPI.getHost() : '127.0.0.1';
            const es = new EventSource(`http://${host}:8000/api/v1/events/stream`);
            window._aegisEventSource = es;
            es.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.event === 'telemetry') {
                        if (AegisRouter.getCurrentPage() === 'command-center') {
                            CommandCenter.loadData();
                        } else if (AegisRouter.getCurrentPage() === 'infrastructure') {
                            InfraMonitoring.load();
                        }
                    } else if (msg.event === 'anomaly') {
                        AegisToast.warning(`AI Anomaly Detected on ${msg.data.source_id}`);
                        if (AegisRouter.getCurrentPage() === 'ai-insights') {
                            AIInsights.load();
                        } else if (AegisRouter.getCurrentPage() === 'incident-dna') {
                            IncidentDNA.load();
                        }
                    }
                } catch(e) {}
            };
        } catch(e) {}
    }

    function setupLoginForm() {
        const form = document.getElementById('login-form');
        const regLink = document.getElementById('register-link');
        const regModal = document.getElementById('register-modal');
        const regClose = document.getElementById('register-close');
        const regForm = document.getElementById('register-form');

        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();
                const email = document.getElementById('login-email').value.trim();
                const password = document.getElementById('login-password').value;
                const btn = form.querySelector('button[type="submit"]');
                const errEl = document.getElementById('login-error');

                btn.disabled = true;
                btn.innerHTML = '<div class="spinner"></div> Signing in...';
                errEl.textContent = '';

                const result = await AegisAuth.login(email, password);

                if (result.success) {
                    if (result.demo) {
                        AegisToast.warning('Running in demo mode — backend not connected');
                    } else {
                        AegisToast.success('Welcome back!');
                    }
                    showApp();
                } else {
                    errEl.textContent = result.error;
                    btn.disabled = false;
                    btn.innerHTML = 'Sign In';
                }
            };
        }

        // Toggle password visibility
        const togglePw = document.getElementById('toggle-password');
        if (togglePw) {
            togglePw.onclick = () => {
                const inp = document.getElementById('login-password');
                const isPassword = inp.type === 'password';
                inp.type = isPassword ? 'text' : 'password';
                togglePw.innerHTML = isPassword ? AegisIcons.eyeOff() : AegisIcons.eye();
            };
        }

        // Registration modal
        if (regLink) regLink.onclick = () => regModal?.classList.add('active');
        if (regClose) regClose.onclick = () => regModal?.classList.remove('active');
        if (regModal) regModal.onclick = (e) => { if (e.target === regModal) regModal.classList.remove('active'); };

        if (regForm) {
            regForm.onsubmit = async (e) => {
                e.preventDefault();
                const data = {
                    org_name: document.getElementById('reg-org-name').value.trim(),
                    admin_email: document.getElementById('reg-email').value.trim(),
                    admin_name: document.getElementById('reg-name').value.trim(),
                    password: document.getElementById('reg-password').value,
                };

                const result = await AegisAuth.register(data);
                if (result.success) {
                    AegisToast.success('Organization registered! You can now sign in.');
                    regModal.classList.remove('active');
                    regForm.reset();
                } else {
                    AegisToast.error(result.error);
                }
            };
        }
    }

    function setupSidebar() {
        const session = AegisAuth.getSession();

        // User info
        const avatarEl = document.getElementById('sidebar-avatar');
        const nameEl = document.getElementById('sidebar-user-name');
        const roleEl = document.getElementById('sidebar-user-role');
        if (session) {
            if (avatarEl) avatarEl.textContent = (session.name || 'U').charAt(0).toUpperCase();
            if (nameEl) nameEl.textContent = session.name || 'User';
            if (roleEl) roleEl.textContent = session.role || 'Member';
        }

        // Nav click handlers
        document.querySelectorAll('.nav-item[data-page]').forEach(item => {
            item.onclick = (e) => {
                e.preventDefault();
                AegisRouter.navigate(item.dataset.page);
            };
        });

        // Logout
        const logoutBtn = document.getElementById('sidebar-logout');
        if (logoutBtn) {
            logoutBtn.onclick = () => {
                AegisAuth.logout();
                AegisToast.info('Signed out');
            };
        }
    }

    function setupRoutes() {
        const content = document.getElementById('content-area');
        AegisRouter.setContentElement(content);

        AegisRouter.setNavigateCallback(path => {
            updateBreadcrumb(path);
        });

        // Register all page modules
        AegisRouter.register('command-center', (el) => CommandCenter.render(el));
        AegisRouter.register('infrastructure', (el) => InfraMonitoring.render(el));
        AegisRouter.register('network', (el) => NetworkMonitoring.render(el));
        AegisRouter.register('security', (el) => SecurityMonitoring.render(el));
        AegisRouter.register('collectors', (el) => CollectorManagement.render(el));
        AegisRouter.register('incident-dna', (el) => IncidentDNA.render(el));
        AegisRouter.register('ai-insights', (el) => AIInsights.render(el));
        AegisRouter.register('privacy-passport', (el) => PrivacyPassport.render(el));
        AegisRouter.register('egress-proof', (el) => EgressProof.render(el));
        AegisRouter.register('audit-center', (el) => AuditCenter.render(el));
        AegisRouter.register('recovery-simulator', (el) => RecoverySimulator.render(el));
        AegisRouter.register('demo-controls', (el) => DemoControls.render(el));
        AegisRouter.register('settings', (el) => OrgSettings.render(el));
    }

    function updateBreadcrumb(path) {
        const pageNames = {
            'command-center': 'Command Center',
            'infrastructure': 'Infrastructure',
            'network': 'Network',
            'security': 'Security',
            'collectors': 'Collectors',
            'incident-dna': 'Incident DNA',
            'ai-insights': 'AI Insights',
            'privacy-passport': 'Privacy Passport',
            'egress-proof': 'Egress Proof',
            'audit-center': 'Audit Center',
            'recovery-simulator': 'Recovery Simulator',
            'demo-controls': 'AI Demo Controls',
            'settings': 'Settings',
        };

        const el = document.getElementById('breadcrumb');
        if (el) {
            el.innerHTML = `
                <span>AEGIS</span>
                <span class="separator">/</span>
                <span class="current">${pageNames[path] || path}</span>`;
        }
    }

    function updateConnectionStatus(connected) {
        const el = document.getElementById('connection-status');
        if (el) {
            el.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            el.innerHTML = `
                <span class="status-dot ${connected ? 'online' : 'offline'}"></span>
                ${connected ? 'Backend Connected' : 'Backend Offline'}`;
        }
    }

    return { init, showLogin, showApp };
})();

window.AegisApp = AegisApp;

// Boot
document.addEventListener('DOMContentLoaded', () => AegisApp.init());
