/**
 * AEGIS API Client — Fetch wrapper with auth, error handling, and connection tracking.
 */

const AegisAPI = (() => {
    let _activeHost = null;

    function getHost() {
        if (_activeHost) return _activeHost;
        if (typeof window !== 'undefined' && window.location && window.location.hostname) {
            return window.location.hostname;
        }
        return '127.0.0.1';
    }

    function getBaseUrl() {
        return `http://${getHost()}:8000/api/v1`;
    }

    let _token = null;
    let _tenantId = 'default';
    let _connected = false;
    let _lastHealth = null;
    let _onConnectionChange = null;
    let _onTenantChange = null;

    function setToken(token) {
        _token = token;
        if (token) {
            localStorage.setItem('aegis_token', token);
        } else {
            localStorage.removeItem('aegis_token');
        }
    }

    function getToken() {
        if (!_token && typeof localStorage !== 'undefined') {
            _token = localStorage.getItem('aegis_token');
        }
        return _token;
    }

    function setTenantId(tid) {
        _tenantId = 'default';
    }

    function getTenantId() {
        return 'default';
    }

    function setTenantChangeCallback(cb) {
        _onTenantChange = cb;
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
        const primaryHost = getHost();
        const fallbackHost = primaryHost === '127.0.0.1' ? 'localhost' : '127.0.0.1';
        const primaryUrl = `http://${primaryHost}:8000/api/v1${path}`;
        const fallbackUrl = `http://${fallbackHost}:8000/api/v1${path}`;

        const headers = {
            'Content-Type': 'application/json',
            'X-Tenant-Id': getTenantId(),
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

        let response;
        try {
            response = await fetch(primaryUrl, config);
            _activeHost = primaryHost;
        } catch (primaryErr) {
            try {
                response = await fetch(fallbackUrl, config);
                _activeHost = fallbackHost;
            } catch (fallbackErr) {
                _updateConnection(false);
                throw new Error(`Cannot connect to AEGIS backend at ${primaryUrl}. Is the server running?`);
            }
        }

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
    }

    // Check backend and genuine database availability via /health
    async function healthCheck() {
        const primary = getHost();
        const fallback = primary === '127.0.0.1' ? 'localhost' : '127.0.0.1';
        for (const h of [primary, fallback]) {
            try {
                const res = await fetch(`http://${h}:8000/health`);
                if (res.ok) {
                    const data = await res.json();
                    _lastHealth = data;
                    _activeHost = h;
                    const isOnline = data.status === 'healthy';
                    _updateConnection(isOnline);
                    return data;
                }
            } catch (err) {
                // Try next host
            }
        }
        _updateConnection(false);
        return { status: 'offline', database: 'unreachable' };
    }

    return {
        setToken,
        getToken,
        setTenantId,
        getTenantId,
        setTenantChangeCallback,
        isAuthenticated,
        setConnectionCallback,
        healthCheck,
        getBaseUrl,
        getHost,
        getLastHealth: () => _lastHealth,
        get: (path, opts) => request('GET', path, null, opts),
        post: (path, body, opts) => request('POST', path, body, opts),
        put: (path, body, opts) => request('PUT', path, body, opts),
        delete: (path, opts) => request('DELETE', path, null, opts),
        get connected() { return _connected; },
    };
})();

window.AegisAPI = AegisAPI;
