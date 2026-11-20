/**
 * AEGIS API Client — Fetch wrapper with auth, error handling, and connection tracking.
 */

const AegisAPI = (() => {
    function getHost() {
        if (typeof window !== 'undefined' && window.location) {
            if (window.location.hostname === '127.0.0.1') return '127.0.0.1';
            if (window.location.hostname && window.location.hostname !== 'localhost') return window.location.hostname;
        }
        return 'localhost';
    }

    function getBaseUrl() {
        return `http://${getHost()}:8000/api/v1`;
    }

    let _token = null;
    let _connected = false;
    let _lastHealth = null;
    let _onConnectionChange = null;

    function setToken(token) {
        _token = token;
        if (token) {
            localStorage.setItem('aegis_token', token);
        } else {
            localStorage.removeItem('aegis_token');
        }
    }

    function getToken() {
        if (!_token) {
            _token = localStorage.getItem('aegis_token');
        }
        return _token;
    }

    function isAuthenticated() {
        return !!getToken();
    }

    function setConnectionCallback(cb) {
        _onConnectionChange = cb;
    }

    function _updateConnection(status) {
        if (_connected !== status) {
            _connected = status;
            if (_onConnectionChange) _onConnectionChange(status);
        }
    }

    async function request(method, path, body = null, options = {}) {
        const url = `${getBaseUrl()}${path}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const token = getToken();
        if (token && !options.noAuth) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            method,
            headers,
        };

        if (body && method !== 'GET') {
            config.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, config);
            _updateConnection(true);

            if (response.status === 401) {
                // Token expired or invalid
                setToken(null);
                if (window.AegisApp) {
                    window.AegisApp.showLogin();
                }
                throw new Error('Authentication expired. Please log in again.');
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (err) {
            if (err.name === 'TypeError' && err.message.includes('fetch')) {
                _updateConnection(false);
                throw new Error(`Cannot connect to AEGIS backend at ${getBaseUrl()}. Is the server running?`);
            }
            throw err;
        }
    }

    // Check backend and genuine database availability via /health
    async function healthCheck() {
        try {
            const host = getHost();
            const res = await fetch(`http://${host}:8000/health`);
            if (res.ok) {
                const data = await res.json();
                _lastHealth = data;
                const isOnline = data.status === 'healthy';
                _updateConnection(isOnline);
                return data;
            }
            _updateConnection(false);
            return { status: 'degraded', database: 'disconnected' };
        } catch (err) {
            _updateConnection(false);
            return { status: 'offline', database: 'unreachable' };
        }
    }

    return {
        setToken,
        getToken,
        isAuthenticated,
        setConnectionCallback,
        healthCheck,
        getBaseUrl,
        getLastHealth: () => _lastHealth,
        get: (path, opts) => request('GET', path, null, opts),
        post: (path, body, opts) => request('POST', path, body, opts),
        put: (path, body, opts) => request('PUT', path, body, opts),
        delete: (path, opts) => request('DELETE', path, null, opts),
        get connected() { return _connected; },
    };
})();

window.AegisAPI = AegisAPI;
