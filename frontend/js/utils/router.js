/**
 * AEGIS Client-Side Router — Hash-based SPA navigation
 */

const AegisRouter = (() => {
    const _routes = {};
    let _currentPage = null;
    let _contentEl = null;
    let _onNavigate = null;

    function register(path, loadFn) {
        _routes[path] = loadFn;
    }

    function setContentElement(el) {
        _contentEl = el;
    }

    function setNavigateCallback(cb) {
        _onNavigate = cb;
    }

    async function navigate(path) {
        if (!_contentEl) return;

        const loader = _routes[path];
        if (!loader) {
            _contentEl.innerHTML = `
                <div class="empty-state">
                    <h3>Page Not Found</h3>
                    <p>The requested module "${path}" does not exist.</p>
                </div>`;
            return;
        }

        // Show loading state
        _contentEl.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:center;height:200px;">
                <div class="spinner"></div>
            </div>`;

        _currentPage = path;
        window.location.hash = path;

        // Update active nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === path);
        });

        if (_onNavigate) _onNavigate(path);

        try {
            await loader(_contentEl);
        } catch (err) {
            console.error(`Error loading page ${path}:`, err);
            _contentEl.innerHTML = `
                <div class="alert alert-danger" style="margin:var(--space-4);">
                    ${AegisIcons.alertTriangle()}
                    <div>
                        <strong>Error loading module</strong><br>
                        <span class="text-sm">${err.message}</span>
                    </div>
                </div>`;
        }
    }

    function getCurrentPage() {
        return _currentPage;
    }

    // Handle browser back/forward
    function init() {
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.slice(1) || 'command-center';
            if (hash !== _currentPage) {
                navigate(hash);
            }
        });
    }

    return { register, setContentElement, setNavigateCallback, navigate, getCurrentPage, init };
})();

window.AegisRouter = AegisRouter;
