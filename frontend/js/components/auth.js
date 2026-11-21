/**
 * AEGIS Auth Module — Login form logic and session management
 */

const AegisAuth = (() => {
    const LOCAL_USERS = [
        { email: 'admin@aegis.io', password: 'aegis2026', name: 'System Administrator', role: 'System Administrator', org: 'AEGIS Server Node', orgId: 'default' },
        { email: 'admin@aegis.local', password: 'aegis2026', name: 'System Administrator', role: 'System Administrator', org: 'AEGIS Server Node', orgId: 'default' },
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
            if (err.message.includes('Cannot connect')) {
                const user = LOCAL_USERS.find(u => u.email === email && u.password === password);
                if (user) {
                    const session = { ...user };
                    delete session.password;
                    AegisAPI.setToken('aegis-session-token');
                    setSession(session);
                    return { success: true, user: session };
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
                return { success: true, data: { message: 'Node registered.' } };
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
