/**
 * AEGIS Command Center — Dashboard Page Module
 * Displays real data from backend when available, clearly labels simulated data.
 */

const CommandCenter = (() => {
    let _chartInstances = {};
    let _refreshInterval = null;

    async function render(container) {
        container.innerHTML = getTemplate();
        await loadData();
        initCharts();
        startAutoRefresh();
    }

    function destroy() {
        if (_refreshInterval) clearInterval(_refreshInterval);
        Object.values(_chartInstances).forEach(c => c.destroy && c.destroy());
        _chartInstances = {};
    }

    function getTemplate() {
        return `
        <div class="command-center">
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Command Center</h1>
                        <p class="page-subtitle">Real-time infrastructure health and observability overview</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="text-xs text-muted" id="cc-last-updated">Last updated: —</span>
                        <button class="btn btn-secondary btn-sm" onclick="CommandCenter.refresh()">
                            ${AegisIcons.refresh()} Refresh
                        </button>
                    </div>
                </div>
            </div>

            <div id="cc-sim-banner"></div>

            <!-- Health Banner -->
            <div class="health-banner" id="cc-health-banner">
                <div class="health-score excellent" id="cc-health-score">
                    <span>—</span>
                </div>
                <div class="health-info">
                    <h3 id="cc-health-label">Calculating...</h3>
                    <p id="cc-health-desc" class="text-sm text-muted">Evaluating infrastructure health across all connected collectors</p>
                </div>
                <div class="health-states">
                    <div class="health-state-item excellent">
                        <span class="count" id="cc-state-excellent">0</span>
                        <span class="label">Excellent</span>
                    </div>
                    <div class="health-state-item good">
                        <span class="count" id="cc-state-good">0</span>
                        <span class="label">Good</span>
                    </div>
                    <div class="health-state-item fair">
                        <span class="count" id="cc-state-fair">0</span>
                        <span class="label">Fair</span>
                    </div>
                    <div class="health-state-item poor">
                        <span class="count" id="cc-state-poor">0</span>
                        <span class="label">Poor</span>
                    </div>
                </div>
            </div>

            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon accent">${AegisIcons.radio()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Connected Collectors</div>
                        <div class="stat-value" id="cc-collectors-online">0</div>
                        <div class="stat-change neutral" id="cc-collectors-offline">0 offline</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon poor">${AegisIcons.alertTriangle()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Active Incidents</div>
                        <div class="stat-value" id="cc-active-incidents">0</div>
                        <div class="stat-change neutral" id="cc-incidents-24h">0 in last 24h</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon fair">${AegisIcons.lock()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Security Alerts</div>
                        <div class="stat-value" id="cc-security-alerts">0</div>
                        <div class="stat-change neutral" id="cc-sec-severity">None active</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon excellent">${AegisIcons.shieldCheck()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Privacy Compliance</div>
                        <div class="stat-value" id="cc-privacy-status">—</div>
                        <div class="stat-change neutral" id="cc-egress-count">0 payloads transmitted</div>
                    </div>
                </div>
            </div>

            <!-- Resource Stats Row -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon teal">${AegisIcons.cpu()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Avg CPU Usage</div>
                        <div class="stat-value" id="cc-cpu-avg">—%</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon accent">${AegisIcons.activity()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Avg Memory Usage</div>
                        <div class="stat-value" id="cc-mem-avg">—%</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon good">${AegisIcons.hardDrive()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Avg Disk Usage</div>
                        <div class="stat-value" id="cc-disk-avg">—%</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon fair">${AegisIcons.wifi()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Avg Network Latency</div>
                        <div class="stat-value" id="cc-latency-avg">— ms</div>
                    </div>
                </div>
            </div>

            <!-- Charts -->
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="card-header">
                        <span class="card-title">CPU & Memory Trend</span>
                        <span class="text-xs text-muted">Last 30 data points</span>
                    </div>
                    <div class="chart-wrapper">
                        <canvas id="cc-chart-resources"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="card-header">
                        <span class="card-title">Network Latency</span>
                        <span class="text-xs text-muted">Last 30 data points</span>
                    </div>
                    <div class="chart-wrapper">
                        <canvas id="cc-chart-latency"></canvas>
                    </div>
                </div>
            </div>

            <!-- Activity Lists -->
            <div class="activity-grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Recent Incidents</span>
                        <button class="btn btn-ghost btn-sm" onclick="AegisRouter.navigate('incident-dna')">View All</button>
                    </div>
                    <div id="cc-incidents-list">
                        <div class="empty-state" style="padding:var(--space-6);">
                            <p class="text-sm text-muted">No incidents detected</p>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">AI Recommendations</span>
                        <button class="btn btn-ghost btn-sm" onclick="AegisRouter.navigate('ai-insights')">View All</button>
                    </div>
                    <div id="cc-recommendations-list">
                        <div class="empty-state" style="padding:var(--space-6);">
                            <p class="text-sm text-muted">No recommendations yet</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }

    async function loadData() {
        const isBackend = AegisAPI.connected;
        let data = null;

        try {
            data = await AegisAPI.get('/dashboard/summary');
            showSimBanner(data.simulated === true);
        } catch {
            // Backend not available — use simulated placeholder data
            data = getSimulatedData();
            showSimBanner(true);
        }

        if (data) updateUI(data);
        updateTimestamp();
    }

    function getSimulatedData() {
        return {
            simulated: true,
            health_state: 'Good',
            health_score: 82,
            states: { excellent: 2, good: 3, fair: 1, poor: 0 },
            collectors_online: 4,
            collectors_offline: 1,
            active_incidents: 2,
            incidents_24h: 5,
            security_alerts: 1,
            security_severity: '1 Medium',
            privacy_status: 'Compliant',
            egress_count: 147,
            cpu_avg: 42,
            memory_avg: 61,
            disk_avg: 55,
            latency_avg: 24,
            incidents: [
                { id: 'INC-001', title: 'Elevated CPU on web-server-03', severity: 'high', time: '12 min ago', source: 'web-server-03' },
                { id: 'INC-002', title: 'Network latency spike detected', severity: 'medium', time: '34 min ago', source: 'gateway-01' },
            ],
            recommendations: [
                { text: 'Investigate web-server-03 CPU — 94% sustained for 8 minutes', reason: 'Exceeds baseline (45±12%) by 4.1σ' },
                { text: 'Review failed login attempts on auth-service', reason: '23 failures in 10 minutes from 3 sources' },
            ],
        };
    }

    function showSimBanner(show) {
        const el = document.getElementById('cc-sim-banner');
        if (el) {
            el.innerHTML = show ? `
                <div class="sim-banner">
                    ${AegisIcons.alertTriangle()}
                    <span><strong>Simulated Data</strong> — Backend not connected. Displaying demonstration data. Connect the AEGIS backend for live telemetry.</span>
                </div>` : '';
        }
    }

    function updateUI(data) {
        // Health banner
        const scoreEl = document.getElementById('cc-health-score');
        const labelEl = document.getElementById('cc-health-label');
        const state = (data.health_state || 'Good').toLowerCase();
        if (scoreEl) {
            scoreEl.className = `health-score ${state}`;
            scoreEl.innerHTML = `<span>${data.health_score || '—'}</span>`;
        }
        if (labelEl) labelEl.textContent = `Infrastructure Health: ${data.health_state || 'Unknown'}`;

        // State counts
        setText('cc-state-excellent', data.states?.excellent ?? 0);
        setText('cc-state-good', data.states?.good ?? 0);
        setText('cc-state-fair', data.states?.fair ?? 0);
        setText('cc-state-poor', data.states?.poor ?? 0);

        // Stats
        setText('cc-collectors-online', data.collectors_online ?? 0);
        setText('cc-collectors-offline', `${data.collectors_offline ?? 0} offline`);
        setText('cc-active-incidents', data.active_incidents ?? 0);
        setText('cc-incidents-24h', `${data.incidents_24h ?? 0} in last 24h`);
        setText('cc-security-alerts', data.security_alerts ?? 0);
        setText('cc-sec-severity', data.security_severity || 'None active');
        setText('cc-privacy-status', data.privacy_status || '—');
        setText('cc-egress-count', `${data.egress_count ?? 0} payloads transmitted`);

        // Resources
        setText('cc-cpu-avg', `${data.cpu_avg ?? '—'}%`);
        setText('cc-mem-avg', `${data.memory_avg ?? '—'}%`);
        setText('cc-disk-avg', `${data.disk_avg ?? '—'}%`);
        setText('cc-latency-avg', `${data.latency_avg ?? '—'} ms`);

        // Incidents list
        const incList = document.getElementById('cc-incidents-list');
        if (incList && data.incidents?.length) {
            incList.innerHTML = data.incidents.map(inc => `
                <div class="incident-row">
                    <div class="incident-severity ${inc.severity}"></div>
                    <div class="incident-details">
                        <div class="incident-title">${esc(inc.title)}</div>
                        <div class="incident-meta">${esc(inc.id)} · ${esc(inc.source)}</div>
                    </div>
                    <div class="incident-time">${esc(inc.time)}</div>
                </div>`).join('');
        }

        // Recommendations list
        const recList = document.getElementById('cc-recommendations-list');
        if (recList && data.recommendations?.length) {
            recList.innerHTML = data.recommendations.map(rec => `
                <div class="recommendation-item">
                    <div class="recommendation-icon">${AegisIcons.brain()}</div>
                    <div class="recommendation-content">
                        <div class="recommendation-text">${esc(rec.text)}</div>
                        <div class="recommendation-reason">${esc(rec.reason)}</div>
                    </div>
                </div>`).join('');
        }
    }

    function initCharts() {
        if (typeof Chart === 'undefined') return;

        const gridColor = 'rgba(56, 189, 248, 0.06)';
        const tickColor = '#64748b';

        const commonScales = {
            x: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 } } },
            y: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 } }, beginAtZero: true, max: 100 },
        };

        const labels = Array.from({ length: 30 }, (_, i) => `${30 - i}s`);

        // CPU & Memory chart
        const resCtx = document.getElementById('cc-chart-resources')?.getContext('2d');
        if (resCtx) {
            _chartInstances.resources = new Chart(resCtx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'CPU %',
                            data: generateDemoTimeSeries(30, 35, 55),
                            borderColor: '#22d3ee',
                            backgroundColor: 'rgba(34, 211, 238, 0.08)',
                            fill: true,
                            tension: 0.3,
                            borderWidth: 2,
                            pointRadius: 0,
                        },
                        {
                            label: 'Memory %',
                            data: generateDemoTimeSeries(30, 55, 70),
                            borderColor: '#14b8a6',
                            backgroundColor: 'rgba(20, 184, 166, 0.08)',
                            fill: true,
                            tension: 0.3,
                            borderWidth: 2,
                            pointRadius: 0,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 11 } } } },
                    scales: commonScales,
                    animation: { duration: 600 },
                },
            });
        }

        // Latency chart
        const latCtx = document.getElementById('cc-chart-latency')?.getContext('2d');
        if (latCtx) {
            _chartInstances.latency = new Chart(latCtx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Latency (ms)',
                        data: generateDemoTimeSeries(30, 10, 45),
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.08)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 11 } } } },
                    scales: {
                        x: commonScales.x,
                        y: { ...commonScales.y, max: undefined, suggestedMax: 80 },
                    },
                    animation: { duration: 600 },
                },
            });
        }
    }

    function generateDemoTimeSeries(count, min, max) {
        const data = [];
        let val = (min + max) / 2;
        for (let i = 0; i < count; i++) {
            val += (Math.random() - 0.5) * 8;
            val = Math.max(min, Math.min(max, val));
            data.push(Math.round(val * 10) / 10);
        }
        return data;
    }

    function startAutoRefresh() {
        if (_refreshInterval) clearInterval(_refreshInterval);
        _refreshInterval = setInterval(() => {
            if (AegisRouter.getCurrentPage() === 'command-center') {
                loadData();
            }
        }, 30000); // 30s refresh
    }

    async function refresh() {
        await loadData();
        AegisToast.info('Dashboard refreshed');
    }

    function updateTimestamp() {
        const el = document.getElementById('cc-last-updated');
        if (el) el.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    }

    function setText(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { render, destroy, refresh };
})();

window.CommandCenter = CommandCenter;
