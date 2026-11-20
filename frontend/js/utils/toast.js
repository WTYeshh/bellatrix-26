/**
 * AEGIS Toast Notification System
 */

const AegisToast = (() => {
    let _container = null;

    function _ensureContainer() {
        if (!_container) {
            _container = document.createElement('div');
            _container.className = 'toast-container';
            document.body.appendChild(_container);
        }
        return _container;
    }

    function show(message, type = 'info', duration = 4000) {
        const container = _ensureContainer();
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const iconMap = {
            success: AegisIcons.check(),
            error: AegisIcons.x(),
            warning: AegisIcons.alertTriangle(),
            info: AegisIcons.bell(),
        };

        toast.innerHTML = `
            <span style="flex-shrink:0;width:16px;height:16px;">${iconMap[type] || iconMap.info}</span>
            <span style="flex:1;">${message}</span>
            <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--color-text-muted);cursor:pointer;padding:2px;">
                ${AegisIcons.x()}
            </button>
        `;

        container.appendChild(toast);

        if (duration > 0) {
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    }

    return {
        success: (msg, dur) => show(msg, 'success', dur),
        error: (msg, dur) => show(msg, 'error', dur),
        warning: (msg, dur) => show(msg, 'warning', dur),
        info: (msg, dur) => show(msg, 'info', dur),
    };
})();

window.AegisToast = AegisToast;
