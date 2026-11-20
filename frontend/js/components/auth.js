/**
 * AEGIS Auth Module — Login form logic and session management
 */

const AegisAuth = (() => {
    // Demo credentials (clearly labelled — backend auth replaces this)
    const DEMO_USERS = [
        { email: 'admin@aegis.io', password: 'aegis2026', name: 'Veeresh M V', role: 'Organization Owner', org: 'AEGIS Demo Corp', orgId: 'ORG_001' },
        { email: 'security@aegis.io', password: 'aegis2026', name: 'Priya Sharma', role: 'Security Engineer', org: 'AEGIS Demo Corp', orgId: 'ORG_001' },
        { email: 'devops@aegis.io', password: 'aegis2026', name: 'Rahul Kumar', role: 'DevOps Engineer', org: 'AEGIS Demo Corp', orgId: 'ORG_001' },
    ];

    function getSession() {
        const raw = localStorage.getItem('aegis_session');
        return raw ? JSON.parse(raw) : null;
    }

    function setSession(user) {
        localStorage.setItem('aegis_session', JSON.stringify({
            ...user,
            loginTime: new Date().toISOString(),
        }));
    }

    function clearSession() {
        localStorage.removeItem('aegis_session');
        localStorage.removeItem('aegis_token');
    }

    async function login(email, password) {
        // Try backend first
        try {
            const data = await AegisAPI.post('/auth/login', { email, password }, { noAuth: true });
            AegisAPI.setToken(data.access_token);
            setSession(data.user);
            return { success: true, user: data.user };
        } catch (err) {
            // If backend unavailable, use demo credentials (clearly labelled)
            if (err.message.includes('Cannot connect')) {
                const user = DEMO_USERS.find(u => u.email === email && u.password === password);
                if (user) {
                    const session = { ...user };
                    delete session.password;
                    AegisAPI.setToken('demo-token-' + Date.now());
                    setSession(session);
                    return { success: true, user: session, demo: true };
                }
                return { success: false, error: 'Invalid email or password.' };
            }
            return { success: false, error: err.message };
        }
    }

    async function register(orgData) {
        try {
            const data = await AegisAPI.post('/auth/register', orgData, { noAuth: true });
            return { success: true, data };
        } catch (err) {
            if (err.message.includes('Cannot connect')) {
                return { success: true, demo: true, data: { message: 'Organization registered (offline demo mode).' } };
            }
            return { success: false, error: err.message };
        }
    }

    function logout() {
        clearSession();
        if (window.AegisApp) {
            window.AegisApp.showLogin();
        }
    }

    return { login, logout, register, getSession, clearSession };
})();

window.AegisAuth = AegisAuth;
